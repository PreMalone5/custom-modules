@http.route('/form_41/download', type='http', auth='user')
def download_form_41_report(self, start_date, end_date, company_id):
    """
    HTTP route handler to generate and download the Form 41 Excel report.

    :param start_date: Start date filter for invoices (string in date format)
    :param end_date: End date filter for invoices (string in date format)
    :param company_id: ID of the company to filter invoices (string or int)
    :return: HTTP response with the generated Excel file for download
    """
    # Create an in-memory bytes buffer to hold the Excel file content
    output = io.BytesIO()

    # Create a new Excel workbook and add a worksheet named "Form 41"
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Form 41")

    # Set worksheet direction to right-to-left for Arabic text support
    worksheet.right_to_left()

    # Define cell formats for headers, second line, and table body
    table_header_format = workbook.add_format({
        'bold': 1,
        'border': 1,
        'bg_color': '#AAB7B8',
        'font_size': '12',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    second_line_format = workbook.add_format({
        # 'border': 1,
        'font_size': 11,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_color': 'red',
        'bg_color': 'red'
    })
    table_body_format = workbook.add_format({
        # 'border': 1,
        'font_size': '11',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })

    # Define a date format for date cells
    date_format = workbook.add_format({'num_format': 'dd.mm.yyyy'})

    # Arabic headers for the report columns
    headers = [
        'مسلسل',
        'رقم التسجيل الضريبي',
        'الرقم القومي',
        'اسم الممول',
        'العنوان',
        'اسم المامورية',
        'كود المامورية',
        'تاريخ التعامل',
        'طبيعة التعامل',
        'القيمة الاجمالية للتعامل',
        'نوع الخصم',
        'تاريخ التعامل للمبلغ المخصوم',
        'القيمة الصافية للتعامل',
        'نسبة الخصم',
        'المحصل لحساب الضريبة'
    ]
    # English second line headers (likely codes or keys)
    second_line = [
        'SERIAL',
        'TAX_REGI_NUM',
        'NATI_ID',
        'TAXPAYEY_NAM',
        'TAXPAY_ADDR',
        'TAX_OFF',
        'COD_OFF',
        'TRNS_DAT',
        'TRNS_TYP',
        'TRNS_VAL',
        'DED_TYPE',
        'DED_AMNT',
        'TRNS_NET_VAL',
        'DED_PRCT',
        'WTHLD_AMT'
    ]

    # Write the headers and second line to the first two rows of the worksheet
    worksheet.write_row(0, 0, headers, table_header_format)
    worksheet.write_row(1, 0, second_line, second_line_format)

    # Query posted vendor bills (invoices) with withholding credit enabled in account lines
    moves = request.env['account.move'].search([
        ('move_type', '=', 'in_invoice'),  # Vendor bills only
        ('state', '=', 'posted'),  # Only posted moves
        ('invoice_date', '>=', start_date),
        ('invoice_date', '<=', end_date),
        ('line_ids.account_id.withholding_credit', '=', True),  # Filter by withholding credit flag
        ('company_id.id', '=', int(company_id))
    ])

    # Start writing data from row 2 (indexing from 0)
    row = 2
    for move in moves:
        # Column 0 (مسلسل) left empty as per original code

        # Column 1 (رقم التسجيل الضريبي): Partner VAT number or blank if zero
        worksheet.write(row, 1, (move.partner_id.vat if move.partner_id.vat != 0 else ' '), table_body_format)

        # Columns 2 to 6 left empty as per original code

        # Column 7 (تاريخ التعامل): Invoice date with date formatting
        worksheet.write(row, 7, move.invoice_date, date_format)

        # Column 8 (طبيعة التعامل): Tax category or blank if zero
        worksheet.write(row, 8, (move.tax_category if move.tax_category != 0 else ' '), table_body_format)

        # Column 9 (القيمة الاجمالية للتعامل): Untaxed amount of the invoice
        worksheet.write(row, 9, move.amount_untaxed, table_body_format)

        # Column 10 (نوع الخصم): Hardcoded as 1 (likely a placeholder or fixed value)
        worksheet.write(row, 10, 1, table_body_format)

        # Column 11 (تاريخ التعامل للمبلغ المخصوم): Invoice date again with date formatting
        worksheet.write(row, 11, move.invoice_date, date_format)

        # Increment row counter for next record
        row += 1

    # Set all columns from A to O to a width of 30 for better readability
    worksheet.set_column('A:O', 30)

    # Hide the second row (index 1) which contains the second line headers
    worksheet.set_row(1, None, None, {'hidden': True})

    # Close the workbook to finalize the Excel file in memory
    workbook.close()

    # Reset buffer position to the beginning before reading
    output.seek(0)

    # Prepare HTTP response with appropriate headers for Excel file download
    response = request.make_response(
        output.read(),
        headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="Form41Report.xlsx"')
        ]
    )

    return response