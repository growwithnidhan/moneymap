from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Expense, Budget, Category
from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
import csv
from django.http import HttpResponse
import json

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

    # Totals
    today_total = sum(e.amount for e in today_expenses)
    month_total = sum(e.amount for e in month_expenses)

    # Get overall budget
    try:
        overall_budget = Budget.objects.get(user=request.user, category__name='Overall')
        daily_limit = overall_budget.daily_limit
        monthly_limit = overall_budget.monthly_limit
    except:
        daily_limit = Decimal('500')
        monthly_limit = Decimal('25000')

    # Budget progress percentages
    daily_percentage = min(float(today_total / daily_limit * 100), 100) if daily_limit > 0 else 0
    monthly_percentage = min(float(month_total / monthly_limit * 100), 100) if monthly_limit > 0 else 0

    # Progress bar colors
    daily_color = 'green' if daily_percentage < 60 else 'yellow' if daily_percentage < 80 else 'red'
    monthly_color = 'green' if monthly_percentage < 60 else 'yellow' if monthly_percentage < 80 else 'red'

    # Warnings
    warnings = []
    if today_total > daily_limit:
        warnings.append(f"🚨 Daily budget exceeded! Spent ₹{today_total} out of ₹{daily_limit} today!")
    elif today_total > daily_limit * Decimal('0.8'):
        warnings.append(f"⚠️ Approaching daily limit! Spent ₹{today_total} out of ₹{daily_limit} today!")

    if month_total > monthly_limit:
        warnings.append(f"🚨 Monthly budget exceeded! Spent ₹{month_total} out of ₹{monthly_limit} this month!")
    elif month_total > monthly_limit * Decimal('0.8'):
        warnings.append(f"⚠️ Approaching monthly limit! Spent ₹{month_total} out of ₹{monthly_limit} this month!")

    # Category wise spending for insights
    category_spending = defaultdict(Decimal)
    for expense in month_expenses:
        category_spending[expense.category.name] += expense.amount

    sorted_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)

    insights = []
    for category, amount in sorted_categories:
        percentage = (amount / month_total * 100) if month_total > 0 else 0
        insights.append({
            'category': category,
            'amount': amount,
            'percentage': round(percentage, 1)
        })

    insights_message = f"💡 You spent the most on {sorted_categories[0][0]} (₹{sorted_categories[0][1]}) this month. Consider reducing this next month!" if sorted_categories else "No expenses this month yet!"

    # Spending trend data for Chart.js
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

# Export to CSV
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