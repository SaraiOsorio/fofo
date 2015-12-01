import re

from openerp import api, tools, SUPERUSER_ID
from openerp.osv import osv, fields, expression
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class product_product(osv.osv):
    _inherit = 'product.product'

    #Product's _rec_name to be -> [code] product name (supplier desc)
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        res = super(product_product, self).name_get(cr, user, ids, context=context)
        products = self.browse(cr, SUPERUSER_ID, ids, context=context)
        supplier_desc = {}
        for product in products:
            supplier_desc[product.id] = product.description_purchase
        final_res = []
        if res:
            for r in res:
                if supplier_desc[r[0]]:
                    final_res.append((r[0], r[1]+' {'+ supplier_desc[r[0]] + '}' ))
                else:
                    final_res.append(r)
        return final_res

    #This method is completly override. Please check #ecosoft tag.
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
                
                if not ids:#ecosoft..
                    ids = self.search(cr, user, [('description_purchase', 'ilike', name)]+ args, limit=limit, context=context)#ecosoft..

            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

product_product()
