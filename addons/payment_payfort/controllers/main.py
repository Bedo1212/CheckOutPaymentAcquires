# -*- coding: utf-8 -*-
import pprint
import logging
import urlparse

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)


class PayfortController(http.Controller):
    _return_url = '/payment/payfort/return/'
    _cancel_url = '/payment/payfort/cancel/'

    @http.route([
        '/payment/payfort/return/',
        '/payment/payfort/cancel/',
    ], type='http', auth='public', csrf=False)
    def payfort_form_feedback(self, **post):
        _logger.info('payfort: entering form_feedback with post data %s', pprint.pformat(post))
        return_url = '/'
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payfort')
            return_url = post.pop('return_url', '/')
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        # Authorize.Net is expecting a response to the POST sent by their server.
        # This response is in the form of a URL that Authorize.Net will pass on to the
        # client's browser to redirect them to the desired location need javascript.
        return request.render('payment_payfort.payment_payfort_redirect', {
            'return_url': '%s' % urlparse.urljoin(base_url, return_url)
        })
