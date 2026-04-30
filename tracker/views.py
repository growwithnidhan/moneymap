from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Expense, Budget, Category
from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
import csv
import json
import io
import calendar
from django.http import HttpResponse

# Register
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Login
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Logout
def logout_view(request):
    logout(request)
    return redirect('login')

# Dashboard
@login_required
def dashboard_view(request):
    today = timezone.now().date()
    expenses = Expense.objects.filter(user=request.user)
    today_expenses = expenses.filter(date=today)
    month_expenses = expenses.filter(date__month=today.month)

    today_total = sum(e.amount for e in today_expenses)
    month_total = sum(e.amount for e in month_expenses)

    try:
        overall_budget = Budget.objects.get(user=request.user, category__name='Overall')
        daily_limit = overall_budget.daily_limit
        monthly_limit = overall_budget.monthly_limit
    except:
        daily_limit = Decimal('500')
        monthly_limit = Decimal('25000')

    daily_percentage = min(float(today_total / daily_limit * 100), 100) if daily_limit > 0 else 0
    monthly_percentage = min(float(month_total / monthly_limit * 100), 100) if monthly_limit > 0 else 0

    daily_color = 'green' if daily_percentage < 60 else 'yellow' if daily_percentage < 80 else 'red'
    monthly_color = 'green' if monthly_percentage < 60 else 'yellow' if monthly_percentage < 80 else 'red'

    warnings = []
    if today_total > daily_limit:
        warnings.append(f"🚨 Daily budget exceeded! Spent ₹{today_total} out of ₹{daily_limit} today!")
    elif today_total > daily_limit * Decimal('0.8'):
        warnings.append(f"⚠️ Approaching daily limit! Spent ₹{today_total} out of ₹{daily_limit} today!")

    if month_total > monthly_limit:
        warnings.append(f"🚨 Monthly budget exceeded! Spent ₹{month_total} out of ₹{monthly_limit} this month!")
    elif month_total > monthly_limit * Decimal('0.8'):
        warnings.append(f"⚠️ Approaching monthly limit! Spent ₹{month_total} out of ₹{monthly_limit} this month!")

    category_spending = defaultdict(Decimal)
    for expense in month_expenses:
        category_spending[expense.category.name] += expense.amount

    sorted_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)

    chart_colors = [
        '#e94560', '#0f3460', '#28a745',
        '#fd7e14', '#6f42c1', '#17a2b8',
        '#ffc107', '#dc3545'
    ]

    insights = []
    for i, (category, amount) in enumerate(sorted_categories):
        percentage = (amount / month_total * 100) if month_total > 0 else 0
        insights.append({
            'category': category,
            'amount': amount,
            'percentage': round(percentage, 1),
            'color': chart_colors[i % len(chart_colors)]
        })

    insights_message = f"💡 You spent the most on {sorted_categories[0][0]} (₹{sorted_categories[0][1]}) this month. Consider reducing this next month!" if sorted_categories else "No expenses this month yet!"

    pie_labels = json.dumps([item['category'] for item in insights])
    pie_data = json.dumps([float(item['amount']) for item in insights])
    pie_colors = json.dumps([item['color'] for item in insights])

    daily_spending = defaultdict(Decimal)
    for expense in month_expenses:
        daily_spending[str(expense.date)] += expense.amount

    sorted_days = sorted(daily_spending.items())
    chart_labels = json.dumps([day for day, _ in sorted_days])
    chart_data = json.dumps([float(amount) for _, amount in sorted_days])

    return render(request, 'dashboard.html', {
        'expenses': expenses,
        'today_total': today_total,
        'month_total': month_total,
        'daily_limit': daily_limit,
        'monthly_limit': monthly_limit,
        'daily_percentage': round(daily_percentage, 1),
        'monthly_percentage': round(monthly_percentage, 1),
        'daily_color': daily_color,
        'monthly_color': monthly_color,
        'warnings': warnings,
        'insights': insights,
        'insights_message': insights_message,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'pie_labels': pie_labels,
        'pie_data': pie_data,
        'pie_colors': pie_colors,
    })

# Add Expense
@login_required
def add_expense_view(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        category_id = request.POST['category']
        amount = request.POST['amount']
        description = request.POST['description']
        category = Category.objects.get(id=category_id)
        Expense.objects.create(
            user=request.user,
            category=category,
            amount=amount,
            description=description
        )
        return redirect('dashboard')
    return render(request, 'add_expense.html', {'categories': categories})

# Set Budget
@login_required
def set_budget_view(request):
    if request.method == 'POST':
        daily_limit = request.POST['daily_limit']
        monthly_limit = request.POST['monthly_limit']
        overall_category, _ = Category.objects.get_or_create(name='Overall')
        Budget.objects.update_or_create(
            user=request.user,
            category=overall_category,
            defaults={
                'daily_limit': daily_limit,
                'monthly_limit': monthly_limit
            }
        )
        return redirect('dashboard')
    return render(request, 'set_budget.html', {})

# Monthly Summary
@login_required
def monthly_summary_view(request):
    expenses = Expense.objects.filter(user=request.user)
    monthly_data = defaultdict(Decimal)
    for expense in expenses:
        month_key = expense.date.strftime('%B %Y')
        monthly_data[month_key] += expense.amount

    sorted_monthly = sorted(monthly_data.items())

    if sorted_monthly:
        max_month = max(sorted_monthly, key=lambda x: x[1])
        summary_message = f"💡 You spent the most in {max_month[0]} — ₹{max_month[1]}"
    else:
        summary_message = "No expenses recorded yet!"

    return render(request, 'monthly_summary.html', {
        'monthly_data': sorted_monthly,
        'summary_message': summary_message,
    })

# Export CSV
@login_required
def export_csv_view(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="moneymap_expenses.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Category', 'Amount'])
    expenses = Expense.objects.filter(user=request.user)
    for expense in expenses:
        writer.writerow([expense.date, expense.description, expense.category.name, expense.amount])
    return response

# Notification Parser
@login_required
def parse_notification_view(request):
    parsed = None
    error = None

    if request.method == 'POST':
        notification_text = request.POST.get('notification_text', '')
        import re

        amount_match = re.search(r'(?:Rs\.?|INR|₹)\s*(\d+(?:\.\d{1,2})?)', notification_text, re.IGNORECASE)
        if not amount_match:
            amount_match = re.search(r'(\d+(?:\.\d{1,2})?)\s*(?:Rs\.?|INR|₹)', notification_text, re.IGNORECASE)

        merchant_match = re.search(r'(?:at|to|@)\s+([A-Za-z0-9\s]+?)(?:\s+on|\s+for|\s+via|\.|,|$)', notification_text, re.IGNORECASE)

        if amount_match:
            amount = Decimal(amount_match.group(1))
            merchant = merchant_match.group(1).strip() if merchant_match else 'Unknown'

            merchant_lower = merchant.lower()
            if any(x in merchant_lower for x in ['zomato', 'swiggy', 'food', 'restaurant', 'cafe', 'pizza', 'burger', 'dominos', 'kfc']):
                category_name = 'Food'
            elif any(x in merchant_lower for x in ['uber', 'ola', 'rapido', 'travel', 'metro', 'bus', 'train', 'flight']):
                category_name = 'Travel'
            elif any(x in merchant_lower for x in ['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'meesho']):
                category_name = 'Shopping'
            elif any(x in merchant_lower for x in ['airtel', 'jio', 'bsnl', 'electricity', 'water', 'bill', 'recharge']):
                category_name = 'Bills'
            elif any(x in merchant_lower for x in ['netflix', 'spotify', 'movie', 'cinema', 'entertainment', 'prime', 'hotstar']):
                category_name = 'Entertainment'
            else:
                category_name = 'Food'

            category, _ = Category.objects.get_or_create(name=category_name)
            Expense.objects.create(
                user=request.user,
                category=category,
                amount=amount,
                description=f"Auto: {merchant}"
            )

            parsed = {
                'amount': amount,
                'merchant': merchant,
                'category': category_name,
                'status': 'success'
            }

            today = timezone.now().date()
            today_expenses = Expense.objects.filter(user=request.user, date=today)
            today_total = sum(e.amount for e in today_expenses)

            try:
                overall_budget = Budget.objects.get(user=request.user, category__name='Overall')
                if today_total > overall_budget.daily_limit:
                    parsed['warning'] = f"🚨 Daily budget exceeded! Spent ₹{today_total} today!"
            except:
                pass
        else:
            error = "Could not extract amount from notification. Please check the format!"

    return render(request, 'parse_notification.html', {
        'parsed': parsed,
        'error': error
    })

# Download Report Page
@login_required
def report_page_view(request):
    return render(request, 'download_report.html', {})

# PDF Report Generator
@login_required
def download_report_view(request):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from datetime import datetime

    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    expenses = Expense.objects.filter(
        user=request.user,
        date__month=month,
        date__year=year
    ).order_by('date')

    try:
        overall_budget = Budget.objects.get(user=request.user, category__name='Overall')
        daily_limit = float(overall_budget.daily_limit)
        monthly_limit = float(overall_budget.monthly_limit)
    except:
        daily_limit = 500
        monthly_limit = 25000

    month_total = sum(float(e.amount) for e in expenses)
    month_name = calendar.month_name[month]

    daily_spending = defaultdict(float)
    for expense in expenses:
        daily_spending[str(expense.date)] += float(expense.amount)

    category_spending = defaultdict(float)
    for expense in expenses:
        category_spending[expense.category.name] += float(expense.amount)

    # ===== PIE CHART =====
    pie_buffer = io.BytesIO()
    if category_spending:
        fig, ax = plt.subplots(figsize=(6, 4.5))
        pie_colors = ['#e94560', '#0f3460', '#28a745', '#fd7e14', '#6f42c1', '#17a2b8', '#ffc107']
        wedges, texts, autotexts = ax.pie(
            category_spending.values(),
            labels=category_spending.keys(),
            autopct='%1.1f%%',
            colors=pie_colors[:len(category_spending)],
            startangle=90,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2.5},
            pctdistance=0.75
        )
        for text in texts:
            text.set_fontsize(9)
            text.set_fontweight('bold')
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        ax.set_title(f'Spending by Category\n{month_name} {year}',
            fontsize=11, fontweight='bold', pad=15, color='#1a1a2e')
        plt.tight_layout()
        plt.savefig(pie_buffer, format='PNG', dpi=150,
            bbox_inches='tight', facecolor='white')
        plt.close()
        pie_buffer.seek(0)

    # ===== LINE CHART =====
    line_buffer = io.BytesIO()
    if daily_spending:
        fig, ax = plt.subplots(figsize=(8, 3.5))
        dates = sorted(daily_spending.keys())
        amounts = [daily_spending[d] for d in dates]
        short_dates = [d[8:] + '/' + d[5:7] for d in dates]
        x_pos = range(len(amounts))

        ax.fill_between(x_pos, amounts, alpha=0.15, color='#e94560')
        ax.plot(x_pos, amounts, color='#e94560', linewidth=2.5,
            marker='o', markersize=6, markerfacecolor='white',
            markeredgecolor='#e94560', markeredgewidth=2, zorder=5)
        ax.axhline(y=daily_limit, color='#ff4444', linestyle='--',
            linewidth=1.5, label=f'Daily Limit ₹{daily_limit:.0f}', alpha=0.8)

        for i, amount in enumerate(amounts):
            if amount > daily_limit:
                ax.scatter(i, amount, color='#e94560', s=100, zorder=6)
                ax.annotate(f'₹{amount:.0f}',
                    (i, amount),
                    textcoords="offset points",
                    xytext=(0, 10),
                    fontsize=7,
                    color='#e94560',
                    fontweight='bold',
                    ha='center')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(short_dates, rotation=45, fontsize=7)
        ax.set_ylabel('Amount (₹)', fontsize=9)
        ax.set_title(f'Daily Spending Trend — {month_name} {year}',
            fontsize=11, fontweight='bold', color='#1a1a2e')
        ax.legend(fontsize=8, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#fafafa')
        plt.tight_layout()
        plt.savefig(line_buffer, format='PNG', dpi=150,
            bbox_inches='tight', facecolor='white')
        plt.close()
        line_buffer.seek(0)

    # ===== BUILD PDF =====
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # ===== STYLES =====
    title_style = ParagraphStyle('Title', fontSize=28,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_CENTER, fontName='Helvetica-Bold',
        spaceAfter=10, spaceBefore=10)

    subtitle_style = ParagraphStyle('Subtitle', fontSize=14,
        textColor=colors.HexColor('#e94560'),
        alignment=TA_CENTER, fontName='Helvetica',
        spaceAfter=10, spaceBefore=5)

    meta_style = ParagraphStyle('Meta', fontSize=9,
        textColor=colors.HexColor('#888888'),
        alignment=TA_CENTER, fontName='Helvetica',
        spaceAfter=15, spaceBefore=5)

    section_style = ParagraphStyle('Section', fontSize=12,
        textColor=colors.HexColor('#ffffff'),
        fontName='Helvetica-Bold', spaceAfter=8,
        spaceBefore=12, leftIndent=8)

    normal_style = ParagraphStyle('Normal2', fontSize=9,
        textColor=colors.HexColor('#444444'),
        fontName='Helvetica', spaceAfter=4)

    footer_style = ParagraphStyle('Footer', fontSize=8,
        textColor=colors.HexColor('#aaaaaa'),
        alignment=TA_CENTER, fontName='Helvetica')

    story = []

    # ===== HEADER =====
    story.append(Spacer(1, 15))
    story.append(Paragraph("Money Map", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Monthly Expense Report — {month_name} {year}", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"User: {request.user.username}  |  Generated: {today}  |  Daily Limit: ₹{daily_limit:.0f}  |  Monthly Limit: ₹{monthly_limit:.0f}",
        meta_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2,
        color=colors.HexColor('#e94560'), spaceAfter=20))

    # ===== SUMMARY CARDS =====
    savings = monthly_limit - month_total
    savings_color = '#28a745' if savings >= 0 else '#e94560'
    status = '✅ Within Budget' if month_total <= monthly_limit else '🚨 Budget Exceeded'
    spent_pct = (month_total / monthly_limit * 100) if monthly_limit > 0 else 0

    summary_data = [
        [
            Paragraph('<font color="#555555"><b>Total Spent</b></font>', styles['Normal']),
            Paragraph('<font color="#555555"><b>Monthly Budget</b></font>', styles['Normal']),
            Paragraph('<font color="#555555"><b>Remaining</b></font>', styles['Normal']),
            Paragraph('<font color="#555555"><b>Used</b></font>', styles['Normal']),
            Paragraph('<font color="#555555"><b>Status</b></font>', styles['Normal']),
        ],
        [
            Paragraph(f'<font size="14" color="#e94560"><b>₹{month_total:.0f}</b></font>', styles['Normal']),
            Paragraph(f'<font size="14" color="#0f3460"><b>₹{monthly_limit:.0f}</b></font>', styles['Normal']),
            Paragraph(f'<font size="14" color="{savings_color}"><b>₹{abs(savings):.0f}</b></font>', styles['Normal']),
            Paragraph(f'<font size="12"><b>{spent_pct:.1f}%</b></font>', styles['Normal']),
            Paragraph(f'<b>{status}</b>', styles['Normal']),
        ]
    ]

    summary_table = Table(summary_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f2f5')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWHEIGHT', (0, 0), (0, 0), 28),
        ('ROWHEIGHT', (0, 1), (0, 1), 45),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # ===== CHARTS SIDE BY SIDE =====
    if category_spending and daily_spending:
        chart_data = [[
            Image(pie_buffer, width=8*cm, height=6*cm),
            Image(line_buffer, width=10*cm, height=6*cm)
        ]]
        chart_table = Table(chart_data, colWidths=[8.5*cm, 10*cm])
        chart_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#dddddd')),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#dddddd')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(chart_table)
        story.append(Spacer(1, 20))

    # ===== DAILY EXPENSE TABLE =====
    daily_header_data = [[Paragraph("  Daily Expense Summary", section_style)]]
    daily_header = Table(daily_header_data, colWidths=[17.5*cm])
    daily_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a1a2e')),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
    ]))
    story.append(daily_header)
    story.append(Spacer(1, 5))

    daily_data = [[
        Paragraph('<b>Date</b>', styles['Normal']),
        Paragraph('<b>Day</b>', styles['Normal']),
        Paragraph('<b>Spent</b>', styles['Normal']),
        Paragraph('<b>Limit</b>', styles['Normal']),
        Paragraph('<b>Difference</b>', styles['Normal']),
        Paragraph('<b>Status</b>', styles['Normal']),
    ]]

    for date_str, amount in sorted(daily_spending.items()):
        day_name = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
        diff = amount - daily_limit
        diff_str = f"+₹{diff:.0f}" if diff > 0 else f"-₹{abs(diff):.0f}"
        diff_color = '#e94560' if diff > 0 else '#28a745'

        if amount > daily_limit:
            status = 'Exceeded'
        elif amount > daily_limit * 0.8:
            status = 'Near Limit'
        else:
            status = 'OK'

        daily_data.append([
            Paragraph(date_str, styles['Normal']),
            Paragraph(day_name, styles['Normal']),
            Paragraph(f'<b>₹{amount:.2f}</b>', styles['Normal']),
            Paragraph(f'₹{daily_limit:.2f}', styles['Normal']),
            Paragraph(f'<font color="{diff_color}"><b>{diff_str}</b></font>', styles['Normal']),
            Paragraph(status, styles['Normal']),
        ])

    if len(daily_data) > 1:
        daily_table = Table(daily_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
        daily_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f2f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 0), (-1, -1), 24),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#eeeeee')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ])
        for i, (date_str, amount) in enumerate(sorted(daily_spending.items()), 1):
            if amount > daily_limit:
                daily_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff0f0'))
            elif amount > daily_limit * 0.8:
                daily_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fffbea'))
        daily_table.setStyle(daily_style)
        story.append(daily_table)
    else:
        story.append(Paragraph("No daily expenses recorded.", normal_style))

    story.append(Spacer(1, 20))

    # ===== ALL TRANSACTIONS =====
    trans_header_data = [[Paragraph("  All Transactions", section_style)]]
    trans_header = Table(trans_header_data, colWidths=[17.5*cm])
    trans_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0f3460')),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
    ]))
    story.append(trans_header)
    story.append(Spacer(1, 5))

    trans_data = [[
        Paragraph('<b>Date</b>', styles['Normal']),
        Paragraph('<b>Description</b>', styles['Normal']),
        Paragraph('<b>Category</b>', styles['Normal']),
        Paragraph('<b>Amount</b>', styles['Normal']),
    ]]

    for expense in expenses:
        trans_data.append([
            Paragraph(str(expense.date), styles['Normal']),
            Paragraph(expense.description[:35], styles['Normal']),
            Paragraph(expense.category.name, styles['Normal']),
            Paragraph(f'<b>₹{float(expense.amount):.2f}</b>', styles['Normal']),
        ])

    if len(trans_data) > 1:
        trans_table = Table(trans_data, colWidths=[3.5*cm, 7*cm, 4*cm, 3*cm])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f2f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 0), (-1, -1), 22),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#eeeeee')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ]))
        story.append(trans_table)
    else:
        story.append(Paragraph("No transactions recorded.", normal_style))

    story.append(Spacer(1, 20))

    # ===== CATEGORY BREAKDOWN =====
    cat_header_data = [[Paragraph("  Category Breakdown", section_style)]]
    cat_header = Table(cat_header_data, colWidths=[17.5*cm])
    cat_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6f42c1')),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
    ]))
    story.append(cat_header)
    story.append(Spacer(1, 5))

    cat_data = [[
        Paragraph('<b>Category</b>', styles['Normal']),
        Paragraph('<b>Amount Spent</b>', styles['Normal']),
        Paragraph('<b>% of Total</b>', styles['Normal']),
        Paragraph('<b>No. of Transactions</b>', styles['Normal']),
    ]]

    for cat, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / month_total * 100) if month_total > 0 else 0
        count = sum(1 for e in expenses if e.category.name == cat)
        cat_data.append([
            Paragraph(f'<b>{cat}</b>', styles['Normal']),
            Paragraph(f'<b>₹{amount:.2f}</b>', styles['Normal']),
            Paragraph(f'{percentage:.1f}%', styles['Normal']),
            Paragraph(str(count), styles['Normal']),
        ])

    cat_data.append([
        Paragraph('<b>TOTAL</b>', styles['Normal']),
        Paragraph(f'<b>₹{month_total:.2f}</b>', styles['Normal']),
        Paragraph('<b>100%</b>', styles['Normal']),
        Paragraph(f'<b>{len(expenses)}</b>', styles['Normal']),
    ])

    if len(cat_data) > 1:
        cat_table = Table(cat_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4*cm])
        cat_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f2f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 0), (-1, -1), 25),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#eeeeee')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#fafafa')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ])
        cat_table.setStyle(cat_style)
        story.append(cat_table)

    story.append(Spacer(1, 30))

    # ===== FOOTER =====
    story.append(HRFlowable(width="100%", thickness=1,
        color=colors.HexColor('#dddddd'), spaceAfter=10))
    story.append(Paragraph(
        "Money Map — Cloud-Based Personal Finance Tracker with DevOps Automation",
        footer_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Report for {request.user.username}  |  {month_name} {year}  |  Generated on {today}",
        footer_style))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MoneyMap_Report_{month_name}_{year}.pdf"'
    return response