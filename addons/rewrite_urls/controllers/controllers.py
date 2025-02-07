# from odoo import http
# from odoo.http import request
# from werkzeug.utils import redirect
# from werkzeug.exceptions import NotFound
# import logging
# from odoo.addons.website_sale.controllers.main import WebsiteSale
# import re
# CODE : Only for page redirect
# class CustomWebsiteSale(WebsiteSale):

#     @http.route([
#     '/<path:seo_friendly_url>',
#     '/shop/<path:seo_friendly_url>',
#     '/shop/category/<path:seo_friendly_url>'
#     ], auth='public', website=True)
#     def handle_seo_urls(self, seo_friendly_url, **kwargs):
#         logging.info(f"Received SEO-friendly URL: {seo_friendly_url}")
#         request_path = request.httprequest.path

#         search_condition = seo_friendly_url
#         if request_path.startswith('/shop/category/'):
#             logging.info("Inside IF")
#             search_condition = f"/shop/category/{seo_friendly_url}"
#         elif request_path.startswith('/shop/'):
#             search_condition = f"/shop/{seo_friendly_url}"
#         else:
#             search_condition = f"/{seo_friendly_url}"
#         seo_url = request.env['rewrite_urls.rewrite_urls'].sudo().search([
#             ('seo_friendly_url', '=', search_condition)
#         ], limit=1)

#         if seo_url:
#             return request.redirect(seo_url.original_url)

#         return request.not_found()
    
# CODE : Only for page fetching
# class CustomWebsiteSale(WebsiteSale):
# # class CustomWebsiteSale(http.Controller):
#     @http.route('/<path:seo_friendly_url>', auth='public', website=True)
#     def find_template(self, seo_friendly_url, **kwargs):
#         URLrecord = request.env['rewrite_urls.rewrite_urls'].sudo().search([
#             ('seo_friendly_url', 'ilike', f"/{seo_friendly_url}")
#         ], limit=1)
#         if(URLrecord):
#             page = request.env['website.page'].search([('url', '=', URLrecord.original_url)], limit=1)
#         else:
#             page = request.env['website.page'].search([('url', '=', f'/{seo_friendly_url}')], limit=1)
#         if page:
#             view = page.view_id
#             if view:
#                 return request.render(view.xml_id or view.id, qcontext=kwargs)
#             else:
#                 logging.info("No view found for the template.")
#         else:
#             # return request.not_found()
#             return request.render("http_routing.404")
        
#     @http.route('/shop/<string:seo_friendly_url>', auth='public', website=True)
#     def handle_product_urls(self, seo_friendly_url, **kwargs):
#         try:
#             URLrecord = request.env['rewrite_urls.rewrite_urls'].sudo().search([
#                 ('seo_friendly_url', 'ilike', f"/shop/{seo_friendly_url}")
#             ], limit=1)
#             if(URLrecord):
#                 url = URLrecord.original_url
#             else:
#                 url = f'/shop/{seo_friendly_url}'
#             try:
#                 parts = url.split('-')
#                 productId = int(re.split(r'[?#]', parts[-1])[0])
#             except (ValueError, IndexError) as e:
#                 productId = None
#             if productId:
#                 product = request.env['product.template'].sudo().search([('id', '=', productId)], limit=1)
#                 logging.info("Product ID is %s and URL is : %s", productId, seo_friendly_url)
#                 category = kwargs.get('category')
#                 search = kwargs.get('search')
#                 if category:
#                     kwargs.pop('category', None)
#                 if search:
#                     kwargs.pop('search', None)
#                 if product and category and search:
#                     return request.render("website_sale.product", self._prepare_product_values(product, str(category), str(search), **kwargs))
#                 elif product and category:
#                     return request.render("website_sale.product", self._prepare_product_values(product, str(category), '', **kwargs))
#                 elif product and search:
#                     return request.render("website_sale.product", self._prepare_product_values(product, '', str(search), **kwargs))
#                 elif product:
#                     return request.render("website_sale.product", self._prepare_product_values(product, '', '', **kwargs))
#             else:
#                 page = request.env['website.page'].search([('url', '=', url)], limit=1)
#                 if page:
#                     view = page.view_id
#                     if view:
#                         return request.render(view.xml_id or view.id, qcontext=kwargs)
#                 # return request.not_found()
#                 return request.render("http_routing.404")
#         except Exception as e:
#             logging.info("Exception being raised in the /shop endpoint %s", e)
#             # return request.not_found()
#             return request.render("http_routing.404")

##########################################################################################
from odoo import http
from odoo.http import request
from werkzeug.utils import redirect
import logging
from odoo.addons.website_sale.controllers.main import WebsiteSale,TableCompute
import re
# from odoo.addons.website_sale.controllers.main.WebsiteSale import TableCompute

import logging, requests, json, math

from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.fields import Command
from odoo.http import request, route
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.website.controllers import main
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.osv import expression
from odoo.tools import lazy, str2bool
from odoo.tools.json import scriptsafe as json_scriptsafe
import tempfile
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)

class CustomWebsiteSale(WebsiteSale):

    @http.route([
    '/<path:seo_friendly_url>',
    '/shop/<path:seo_friendly_url>',
    '/shop/category/<path:seo_friendly_url>'
    ], auth='public', website=True)
    def handle_seo_urls(self, seo_friendly_url, **kwargs):
        _logger.info(f"Received SEO-friendly URL: {seo_friendly_url}")

        request_path = request.httprequest.path
        search_condition = f"{request_path}" if request_path.startswith(("/shop", "/shop/category")) else f"/{seo_friendly_url}"
        _logger.info(f"Searching for SEO-friendly URL: {search_condition}")

        seo_url = request.env['rewrite_urls.rewrite_urls'].sudo().search([
            ('seo_friendly_url', '=', search_condition)
        ], limit=1)

        if seo_url:
            _logger.info(f"Found SEO URL: {seo_url.original_url}, Fetch Content: {seo_url.fetch_content}")
            if seo_url.fetch_content:
                if request_path.startswith("/shop/category"):
                    category_id = int(re.split(r'[?#]', seo_url.original_url.split('-')[-1])[0])
                    return self.shop(category=category_id, **kwargs)
                return self.find_template(seo_friendly_url, **kwargs)
            return request.redirect(seo_url.original_url)

        _logger.warning(f"No matching SEO URL found for: {seo_friendly_url}. Returning 404.")
        return request.not_found()


    def find_template(self, seo_friendly_url, **kwargs):
        """Handles rendering pages when fetch_content is True"""
        _logger.info(f"Attempting to render page for SEO-friendly URL: {seo_friendly_url}")

        request_path = request.httprequest.path
        is_shop_page = request_path.startswith('/shop')

        if is_shop_page:
            _logger.info("Detected `/shop` URL. Searching for categories and products.")

            # Search for a matching URL record
            URLrecord = request.env['rewrite_urls.rewrite_urls'].sudo().search([
                ('seo_friendly_url', 'ilike', f"/shop/{seo_friendly_url}")
            ], limit=1)

            url = URLrecord.original_url if URLrecord else f'/shop/{seo_friendly_url}'

            try:
                parts = url.split('-')
                productId = int(re.split(r'[?#]', parts[-1])[0])
            except (ValueError, IndexError) as e:
                _logger.warning(f"Failed to extract product ID from URL: {url}. Error: {e}")
                productId = None

            if productId:
                product = request.env['product.template'].sudo().search([('id', '=', productId)], limit=1)
                _logger.info(f"Product ID: {productId}, Product Name: {product.name if product else 'Not Found'}")

                category = kwargs.pop('category', None)
                search = kwargs.pop('search', None)

                _logger.info(f"Rendering product page with Category: {category}, Search: {search}")

                if product:
                    return request.render("website_sale.product", self._prepare_product_values(product, category or '', search or '', **kwargs))

            _logger.info(f"No product found for {seo_friendly_url}. Checking for website pages.")

            # If no product is found, check for a website page
            page = request.env['website.page'].sudo().search([('url', '=', url)], limit=1)
            if page and page.view_id:
                _logger.info(f"Page found: {page.name}, Rendering view: {page.view_id.xml_id or page.view_id.id}")
                return request.render(page.view_id.xml_id or page.view_id.id, qcontext=kwargs)

        _logger.warning(f"No matching product or page found for {seo_friendly_url}. Returning 404.")
        return request.render("http_routing.404")

    # @route('/shop/category/<path:seo_friendly_url>', auth='public', website=True)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        _logger.info("################## New one route called ##################")
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        request_args = request.httprequest.args
        attrib_list = request_args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        filter_by_tags_enabled = website.is_view_active('website_sale.filter_products_tags')
        if filter_by_tags_enabled:
            tags = request_args.getlist('tags')
            # Allow only numeric tag values to avoid internal error.
            if tags and all(tag.isnumeric() for tag in tags):
                post['tags'] = tags
                tags = {int(tag) for tag in tags}
            else:
                post['tags'] = None
                tags = {}

        keep = QueryURL('/shop', **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post))

        now = datetime.timestamp(datetime.now())
        pricelist = website.pricelist_id
        if 'website_sale_pricelist_time' in request.session:
            # Check if we need to refresh the cached pricelist
            pricelist_save_time = request.session['website_sale_pricelist_time']
            if pricelist_save_time < now - 60*60:
                request.session.pop('website_sale_current_pl', None)
                website.invalidate_recordset(['pricelist_id'])
                pricelist = website.pricelist_id
                request.session['website_sale_pricelist_time'] = now
                request.session['website_sale_current_pl'] = pricelist.id
        else:
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.sudo().currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, website.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = '/shop'
        if search:
            post['search'] = search
        if attrib_list:
            post['attrib'] = attrib_list

        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            display_currency=website.currency_id,
            **post
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search, website)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_shop_domain(search, category, attrib_values)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        ProductTag = request.env['product.tag']
        if filter_by_tags_enabled and search_product:
            all_tags = ProductTag.search(
                expression.AND([
                    [('product_ids.is_published', '=', True), ('visible_on_ecommerce', '=', True)],
                    website_domain
                ])
            )
        else:
            all_tags = ProductTag

        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=5, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        # Try to fetch geoip based fpos or fallback on partner one
        fiscal_position_sudo = website.fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position_sudo))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'fiscal_position': fiscal_position_sudo,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = math.floor(tools.float_round(available_min_price, 2)/ 10) * 10
            values['available_max_price'] = math.ceil(tools.float_round(available_max_price, 2)/ 10) * 10
        if filter_by_tags_enabled:
            values.update({'all_tags': all_tags, 'tags': tags})
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))
        return request.render("website_sale.products", values)


