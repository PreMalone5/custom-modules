from odoo import http
from odoo.http import request
import xlsxwriter
import io
from urllib.parse import quote

class XlsxContReport(http.Controller):

    @http.route('/property/excel/report', type='http', auth='user')
    def download_cont_report(self):

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        workbook.set_calc_mode('auto')
        worksheet = workbook.add_worksheet("المحفظه الاجماليه")
        worksheet.right_to_left()


                                                        # Table 1

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

        # 1. Get all records
        records = request.env['property'].search([])

        # 2. Unique investors and projects
        investors = sorted(set(rec.partner_id for rec in records), key=lambda p: p.name)
        projects = sorted(set(rec.project_id for rec in records), key=lambda p: p.name)

        # 3. Matrix: (project_id, partner_id) → invested_amount
        matrix = {
            (rec.project_id.id, rec.partner_id.id): rec.invested_amount
            for rec in records
        }
        ratio_matrix = {
            (rec.project_id.id, rec.partner_id.id): rec.invest_ratio
            for rec in records
        }

        # 4. Title row
        total_columns = len(investors) + 2
        worksheet.merge_range(0, 0, 0, total_columns, "إجمالي أصول الاستثمار", title_fmt)

        # 5. Header row (row 1)
        worksheet.write(1, 0, "المشروعات", header_fmt)
        for col, investor in enumerate(investors, start=1):
            worksheet.write(1, col, investor.name, header_fmt)
        worksheet.write(1, len(investors) + 1, "إجمالي", header_fmt)

        # 6. Data rows (start at row 2)
        for row, project in enumerate(projects, start=2):
            worksheet.write(row, 0, project.name, header_fmt)
            for col, investor in enumerate(investors, start=1):
                amount = matrix.get((project.id, investor.id), 0.0)
                worksheet.write(row, col, amount, money_fmt)

        # Row index tracking
        project_total_row = len(projects) + 2
        percentage_row = len(projects) + 3
        grand_total_col = len(investors) + 1

        # 7. إجمالي الأصول (column totals)
        worksheet.write(project_total_row, 0, "إجمالي الأصول", total_fmt)
        for col in range(1, len(investors) + 1):
            start_cell = f"{xlsx_col(col)}3"
            end_cell = f"{xlsx_col(col)}{project_total_row}"
            worksheet.write_formula(project_total_row, col, f"=SUM({start_cell}:{end_cell})", total_fmt)

        # 8. إجمالي المشروع (row totals)
        for row in range(2, len(projects) + 2):
            worksheet.write(row, len(investors) + 1,
                            f"=SUM(B{row + 1}:{xlsx_col(len(investors))}{row + 1})", total_fmt)

        # 9. Grand total
        grand_total_formula_range = f"{xlsx_col(1)}{project_total_row + 1}:{xlsx_col(len(investors))}{project_total_row + 1}"
        # worksheet.write(project_total_row, grand_total_col + 1, "إجمالي عام", total_fmt)
        worksheet.write_formula(project_total_row, grand_total_col,
                                f"=SUM({grand_total_formula_range})", total_fmt)

        # 10. نسبة المساهمة الإجمالية
        worksheet.write(percentage_row, 0, "نسبة المساهمة الإجمالية", total_fmt)
        for col in range(1, len(investors) + 1):
            total_cell = f"{xlsx_col(col)}{project_total_row + 1}"
            grand_cell = f"{xlsx_col(grand_total_col)}{project_total_row + 1}"
            formula = f"=IF({grand_cell}=0, 0, {total_cell}/{grand_cell})"
            worksheet.write_formula(percentage_row, col, formula, percent_fmt)

        # 11. Sum of % contributions
        # worksheet.write(percentage_row, grand_total_col + 1, "المجموع %", total_fmt)
        worksheet.write_formula(
            percentage_row,
            grand_total_col,
            f"=SUM({xlsx_col(1)}{percentage_row + 1}:{xlsx_col(len(investors))}{percentage_row + 1})",
            percent_fmt
        )

        # ===============================
        # Table 2: Ratio Table
        # ===============================

        ratio_start_row = percentage_row + 3  # Leave some space

        worksheet.merge_range(ratio_start_row, 0, ratio_start_row, total_columns, "نسب المساهمة في المشاريع", title_fmt)

        # Header for ratio table
        ratio_header_row = ratio_start_row + 1
        worksheet.write(ratio_header_row, 0, "المشروعات", header_fmt)
        for col, investor in enumerate(investors, start=1):
            worksheet.write(ratio_header_row, col, investor.name, header_fmt)
        worksheet.write(ratio_header_row, len(investors) + 1, "إجمالي", header_fmt)

        # Data rows using invest_ratio instead of invested_amount
        for row, project in enumerate(projects, start=ratio_header_row + 1):
            worksheet.write(row, 0, project.name, header_fmt)
            for col, investor in enumerate(investors, start=1):
                ratio = ratio_matrix.get((project.id, investor.id), 0.0)
                worksheet.write(row, col, ratio / 100.0, percent_fmt)

        # إجمالي المشروع (row total of ratios)
        for row in range(ratio_header_row + 1, ratio_header_row + 1 + len(projects)):
            worksheet.write(row, len(investors) + 1,
                            f"=SUM(B{row + 1}:{xlsx_col(len(investors))}{row + 1})", percent_fmt)

        # ===============================
        # Table 3: Profit Table
        # ===============================

        profit_start_row = ratio_start_row + len(projects) + 3  # Leave some space between Table 2 and Table 3

        worksheet.merge_range(profit_start_row, 0, profit_start_row, total_columns, "حصص المساهم من الرصيد", title_fmt)

        # Header for profit table
        profit_header_row = profit_start_row + 1
        worksheet.write(profit_header_row, 0, "المشروعات", header_fmt)
        for col, investor in enumerate(investors, start=1):
            worksheet.write(profit_header_row, col, investor.name, header_fmt)
        worksheet.write(profit_header_row, len(investors) + 1, "إجمالي", header_fmt)

        # Data rows using investor_profit instead of invest_ratio
        for row, project in enumerate(projects, start=profit_header_row + 1):
            worksheet.write(row, 0, project.name, header_fmt)
            for col, investor in enumerate(investors, start=1):
                # Assuming investor_profit is in the property record, use it here
                profit = next((rec.investor_profit for rec in records if
                               rec.project_id == project and rec.partner_id == investor), 0.0)
                worksheet.write(row, col, profit, money_fmt)

        # إجمالي المشروع (row total of profits)
        for row in range(profit_header_row + 1, profit_header_row + 1 + len(projects)):
            worksheet.write(row, len(investors) + 1,
                            f"=SUM(B{row + 1}:{xlsx_col(len(investors))}{row + 1})", money_fmt)

        # 1. إجمالي المستثمرين (total for each investor)
        investor_total_row = profit_header_row + len(projects) + 1  # Row after all the project rows

        worksheet.write(investor_total_row, 0, "إجمالي المستثمرين", total_fmt)

        # For each investor, calculate the total profit across all projects
        for col in range(1, len(investors) + 1):
            # Calculate the sum of profits for each investor across all rows
            start_cell = f"{xlsx_col(col)}{profit_header_row + 2}"
            end_cell = f"{xlsx_col(col)}{profit_header_row + len(projects) + 1}"
            worksheet.write_formula(investor_total_row, col, f"=SUM({start_cell}:{end_cell})", total_fmt)

        # 2. إجمالي عام (grand total for all investors)
        worksheet.write_formula(investor_total_row, len(investors) + 1,
                                f"=SUM(B{investor_total_row + 1}:{xlsx_col(len(investors))}{investor_total_row + 1})",
                                total_fmt)

        # Final touches
        worksheet.freeze_panes(2, 1)
        worksheet.set_column('A:Z', 22)

        workbook.close()
        output.seek(0)

        ascii_filename = "report.xlsx"
        utf8_filename = quote("المحفظه الاجماليه.xlsx")
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{utf8_filename}"),
            ]
        )

def xlsx_col(idx):
    """Convert 0-based index to Excel-style column letter (supports > 26 columns)."""
    result = ""
    while idx >= 0:
        idx, rem = divmod(idx, 26)
        result = chr(rem + 65) + result
        idx -= 1
    return result