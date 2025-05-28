from odoo import http
from odoo.http import request
import xlsxwriter
import io
from urllib.parse import quote
from xlsxwriter.utility import xl_range

class XlsxCustReport(http.Controller):

    @http.route('/contacts/excel/report/<int:partner_id>', type='http', auth='user')
    def download_cust_report(self, partner_id):

        Property = request.env['property'].sudo()
        partner = request.env['res.partner'].sudo().browse(partner_id)
        records = Property.search([('partner_id', '=', partner_id)])
        project_ids = list(set(records.mapped('project_id.name')))

        columns = ['x_project_cost', 'invested_amount', 'invest_ratio', 'x_project_profit', 'investor_profit']
        field_labels = {
            'x_project_cost': 'رأس المال العام',
            'invested_amount': 'حصة المساهم من رأس المال',
            'invest_ratio': 'النسبة',
            'x_project_profit': 'اجمالي الإيرادات الحالية',
            'investor_profit': 'حصة المساهم من الإيرادات'
        }

        data = {field: [] for field in columns}

        for field in columns:
            for proj in project_ids:
                record = records.filtered(lambda r: r.project_id.name == proj)
                value = getattr(record[0], field, 0.0) if record else 0.0
                if field == 'invest_ratio':
                    value = value / 100  # Convert invest_ratio to decimal
                data[field].append(value)

            # Add total except for invest_ratio
            if field == 'invest_ratio':
                data[field].append('')  # Leave total cell empty
            else:
                data[field].append(sum(data[field]))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("كشف الحسابات الجارية (الحالية)")
        worksheet.right_to_left()

        # Formats
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 18,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E78', 'font_color': '#FFFFFF'
        })

        header_fmt = workbook.add_format({
            'bold': True, 'font_size': 12,
            'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True
        })

        money_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'bg_color': '#FDFEFE'
        })

        percent_fmt = workbook.add_format({
            'num_format': '0.00%', 'border': 1,
            'bg_color': '#E2EFDA',
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True
        })

        total_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#B7E1CD',
            'border': 1, 'num_format': '#,##0.00',
            'align': 'center', 'valign': 'vcenter'
        })

        # Title
        total_columns = len(project_ids) + 2
        worksheet.merge_range(0, 0, 0, total_columns, f"{partner.name}", title_fmt)

        # Header
        worksheet.write(1, 0, 'المشروعات', header_fmt)
        for idx, proj in enumerate(project_ids):
            worksheet.write(1, idx + 1, proj, header_fmt)
        worksheet.write(1, len(project_ids) + 1, 'إجمالي', header_fmt)

        # Data Rows
        row_idx = 2
        for field in columns:
            worksheet.write(row_idx, 0, field_labels.get(field, field), header_fmt)
            for col_idx, val in enumerate(data[field]):
                is_total_col = (col_idx == len(data[field]) - 1)
                fmt = total_fmt if is_total_col else (percent_fmt if 'ratio' in field else money_fmt)
                worksheet.write(row_idx, col_idx + 1, val, fmt)
            row_idx += 1

        # Add wallet balance row (only in total column)
        wallet = request.env['investor.wallet'].sudo().search([('partner_id', '=', partner_id)], limit=1)
        balance_value = wallet.balance if wallet else 0.0

        worksheet.write(row_idx, 0, 'الرصيد الحالي', header_fmt)
        worksheet.write(row_idx, len(project_ids) + 1, balance_value, total_fmt)

        worksheet.freeze_panes(2, 1)
        worksheet.set_column('A:Z', 22)

        workbook.close()
        output.seek(0)

        ascii_filename = "report.xlsx"
        utf8_filename = quote("كشف حساب.xlsx")
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{utf8_filename}"),
            ]
        )
