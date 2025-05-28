from odoo import http
from odoo.http import request
import xlsxwriter
import io
from urllib.parse import quote

class XlsxProjReport(http.Controller):

    @http.route('/projects/excel/report/<int:project_id>', type='http', auth='user')
    def download_proj_report(self, project_id):
        # Get project record
        project = request.env['project.project'].sudo().browse(project_id)
        if not project.exists():
            return request.not_found()

        # Fetch data from 'property' model
        props = request.env['property'].sudo().search([('project_id', '=', project.id)])

        # Get unique partner_ids from those properties
        partner_ids = props.mapped('partner_id')

        # Prepare column headers
        header = ['Project: ' + (project.name or 'Unnamed Project')] + [p.name for p in partner_ids] + ['إجمالي']

        # Prepare rows with updated names
        invested_amounts = ['مبلغ المساهمة']
        invest_ratios = ['نسبة المساهمة %']
        investor_profits = ['إجمالي الإيرادات']

        total_invested = 0
        total_profit = 0
        total_ratio = 0

        for partner in partner_ids:
            p_props = props.filtered(lambda x: x.partner_id.id == partner.id)

            invested = sum(p_props.mapped('invested_amount'))
            profit = sum(p_props.mapped('investor_profit'))
            ratio = sum(p_props.mapped('invest_ratio')) / 100.0  # Assuming 17 means 17%

            invested_amounts.append(invested)
            investor_profits.append(profit)
            invest_ratios.append(ratio)

            total_invested += invested
            total_profit += profit
            total_ratio += ratio

        invested_amounts.append(total_invested)
        invest_ratios.append(total_ratio)
        investor_profits.append(total_profit)

        data = [invested_amounts, invest_ratios, investor_profits]

        # Start Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet_name = project.name or "Project Report"
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.right_to_left()
        worksheet.set_column('A:Z', 22)
        worksheet.freeze_panes(1, 1)

        # Formats
        header_fmt = workbook.add_format({
            'bold': True, 'font_size': 12,
            'bg_color': '#D9E1F2', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True
        })
        money_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'border': 1,
            'align': 'center', 'valign': 'vcenter'
        })
        percent_fmt = workbook.add_format({
            'num_format': '0%', 'border': 1,
            'align': 'center', 'valign': 'vcenter'
        })

        # Write headers (include project name in top row)
        worksheet.write_row(0, 0, header, header_fmt)

        # Write data
        for row_idx, row in enumerate(data, start=1):
            worksheet.write(row_idx, 0, row[0], header_fmt)
            for col_idx, value in enumerate(row[1:], start=1):
                fmt = percent_fmt if row[0] == 'نسبة المساهمة %' else money_fmt
                worksheet.write_number(row_idx, col_idx, value, fmt)

        workbook.close()
        output.seek(0)

        ascii_filename = "report.xlsx"
        utf8_filename = quote(f"{project.name or 'Project'}.xlsx")

        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{utf8_filename}"),
            ]
        )
