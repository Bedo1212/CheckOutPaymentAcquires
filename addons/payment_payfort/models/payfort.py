# -*- coding: utf-'8' "-*-"

import hashlib
import hmac
import logging
import time
import urlparse

from openerp import api, fields, models
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_payfort.controllers.main import PayfortController
from openerp.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirerPayfort(models.Model):
    _inherit = 'payment.acquirer'

    def _get_payfort_urls(self, environment):
        """ Payfort URLs """
        if environment == 'prod':
            return {'payfort_form_url': 'https://sbcheckout.payfort.com/FortAPI/paymentPage'}
        else:
            return {'payfort_form_url': 'https://sbcheckout.payfort.com/FortAPI/paymentPage'}

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirerPayfort, self)._get_providers()
        providers.append(['payfort', 'payfort.com'])
        return providers

    provider = fields.Selection(selection_add=[('payfort', 'Payfort')])
    payfort_login = fields.Char(string='API Login Id', required_if_provider='payfort')
    payfort_transaction_key = fields.Char(string='API Transaction Key', required_if_provider='payfort')

    def _payfort_generate_hashing(self, values):
        data = ''.join([
            'zsfas21'
            +'access_code='+values['access_code'],
            'amount='+ values['amount'],
            'command=' +values['command'],
            'currency=' +values['currency'],
            'customer_email=' +values['customer_email'],
            'language=' +values['language'],
            'merchant_identifier=' +values['merchant_identifier'],
            'merchant_reference=' +values['merchant_reference'],
            'return_url=' +values['return_url']+'zsfas21'


        ])
        enc = data.encode('utf-8')
        h = hashlib.sha256(enc)
        return h.hexdigest()
        #return hmac.new(data, hashlib.sha256).hexdigest()

    @api.multi
    def payfort_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        payfort_tx_values = dict(values)
        temp_payfort_tx_values = {
            'command': "PURCHASE",
            'customer_email': 'ebead100@hotmail.com',
            'amount' :str(values['amount']).split('.', 1)[0]+'00',
            'currency' : 'AED',
            'merchant_reference' : values.get('reference'), #'SO-'+'%s%s' % (self.id, int(time.time())),
            'access_code' : 'sdAxboZjcPDrR4qXF080',
            'merchant_identifier' : 'CVOjYLUY',
            'language' :'en' ,


        }
        temp_payfort_tx_values['return_url'] =  'http://94.200.16.6:8090/payment/payfort/return'#payfort_tx_values.pop('return_url', '')
        temp_payfort_tx_values['signature'] = self._payfort_generate_hashing(temp_payfort_tx_values)
       # payfort_tx_values.update(temp_payfort_tx_values)

        return temp_payfort_tx_values

    @api.multi
    def payfort_get_form_action_url(self):
        self.ensure_one()
        return self._get_payfort_urls(self.environment)['payfort_form_url']


class TxPayfort(models.Model):
    _inherit = 'payment.transaction'

    _payfort_valid_tx_status = 14
    _payfort_pending_tx_status = 4
    _payfort_cancel_tx_status = 2

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _payfort_form_get_tx_from_data(self, data):
        """ Given a data dict coming from authorize, verify it and find the related
        transaction record. """
        reference, trans_id, fingerprint = data.get('merchant_reference'), data.get('fort_id'), data.get('signature')
        if not reference or not trans_id or not fingerprint:
            error_msg = 'payfort: received data with missing reference (%s) or trans_id (%s) or fingerprint (%s)' % (reference, trans_id, fingerprint)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Authorize: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    @api.model
    def _payfort_form_get_invalid_parameters(self, tx, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('fort_id') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('fort_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('amount'), '%.2f' % tx.amount))
        return invalid_parameters

    @api.model
    def _payfort_form_validate(self, tx, data):
        if tx.state == 'done':
            _logger.warning('payfort: trying to validate an already validated tx (ref %s)' % tx.reference)
            return True
        status_code = int(data.get('x_response_code', '0'))
        if status_code == self._payfort_valid_tx_status:
            tx.write({
                'state': 'done',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        elif status_code == self._payfort_pending_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        elif status_code == self._payfort_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        else:
            error = data.get('x_response_reason_text')
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('x_trans_id'),
            })
            return False
