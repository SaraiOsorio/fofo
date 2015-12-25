from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from datetime import datetime
import csv
import StringIO
import base64
import xlrd
from openerp import tools
from _abcoll import ItemsView

class import_customer_payment(models.TransientModel):
    _name = 'import.customer.payment'

    input_file = fields.Binary('Input File')

    @api.multi
    def import_payments(self):
        for line in self:
            lines = xlrd.open_workbook(file_contents=base64.decodestring(self.input_file))
            print "---------lines",lines
            for sheet_name in lines.sheet_names(): 
                sheet = lines.sheet_by_name(sheet_name)
                rows = sheet.nrows
                columns = sheet.ncols
                print "-rows--columns------",rows,columns
                print "---------==sheet.row_values(0)==",sheet.row_values(0)
                
                seller_sku = sheet.row_values(0).index('Seller SKU')
                created_at = sheet.row_values(0).index('Created at')
                order_number = sheet.row_values(0).index('Order Number')
                unit_price = sheet.row_values(0).index('Unit Price')
                status = sheet.row_values(0).index('Status')