from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django import forms
from .forms import OTPForm, EmailForm
from cart.models import Cart, displayed_items
from inventory.models import product
from transaction.models import productTransaction, transaction, Profile, Customer
from transaction.views import DateSelector
from plotly import express as px
from plotly import offline as po
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import pandas as pd
import pytz, os, shutil, random, json
import logging
logger = logging.getLogger(__name__)

tz = pytz.timezone("US/Eastern")


class EnterBarcode(forms.Form):
    name = forms.CharField(
        label="Name",
        widget=forms.TextInput(attrs={'style': "width:100%"}),
        max_length=100, required=False 
    )
    barcode = forms.CharField(
        widget=forms.TextInput(attrs={'autofocus': "autofocus", 'autocomplete': "off", 'style': "width:100%"}),
        max_length=32, required=False
    )
    qty = forms.IntegerField(
        label="Quantity",
        widget=forms.TextInput(attrs={'style': "width:100%"}), required=False 
    )


@login_required(login_url="/user/login/")
def register(request):
    form = EnterBarcode(initial={'qty': 0})

    if request.method == "POST":
        customer_id = request.POST.get('customer_id', None)
        customer_number = request.POST.get('customer_number', None)
        customer_name = request.POST.get('customer_name', None)

        # Save the customer info in the session, if needed
        request.session['customer_id'] = customer_id if customer_id else 'not_provided'
        request.session['customer_number'] = customer_number if customer_number else 'not_provided'
        request.session['customer_name'] = customer_name if customer_name else ''

        form = EnterBarcode(request.POST)
        if form.is_valid():
            barcode = form.cleaned_data.get('barcode', '').strip()
            qty = form.cleaned_data.get('qty')  # Default to 1 if no quantity is provided
            name = form.cleaned_data.get('name', '').strip()

            if barcode:
                return redirect(f"/cart/add/{barcode}/{qty}")
            elif name:
                if not name:
                    return redirect('/register/?ProductNotFound=true')
                
                # Perform case-insensitive search for the product name
                try:
                    product_obj = product.objects.get(name__iexact=name)
                    print(f"Product found for name '{name}': Barcode: {product_obj.barcode}")
                    return redirect(f"/cart/add/{product_obj.barcode}/{qty}")
                except product.DoesNotExist:
                    print(f"Product with name '{name}' not found.")
                    return redirect(f"/register/?ProductNotFound=true")

    try:
        cart = request.session[settings.CART_SESSION_ID]
        Total = round(pd.DataFrame(cart).T["line_total"].astype(float).sum(), 2)
        Tax_Total = round(pd.DataFrame(cart).T["tax_value"].astype(float).sum(), 2)
    except KeyError:
        cart = {}
        Total = 0
        Tax_Total = 0

    context = {
        'form': form,
        'no_product': True if "ProductNotFound" in request.path else False,
        'cart': cart,
        'total': Total,
        'tax_total': Tax_Total,
        'displayed_items': displayed_items.objects.all(),
    }
    request.session["Total"] = Total
    request.session["Tax_Total"] = Tax_Total
    request.session.modified = True
    return render(request, 'retailScreen.html', context=context)


@login_required(login_url="/user/login/")
def search_customer(request):
    customer_number = request.GET.get('customer_number', '').strip()
    customer_name = request.GET.get('customer_name', '').strip()

    # Filter customers based on the search inputs
    customers = Customer.objects.all()

    if customer_number:
        customers = customers.filter(customer_contact__icontains=customer_number)

    if customer_name:
        customers = customers.filter(customer_name__icontains=customer_name)

    # Prepare customer data to send back as JSON
    customer_data = []
    for customer in customers:
        customer_data.append({
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name if customer.customer_name != '' else 'No Name' ,
            'customer_contact': customer.customer_contact,
            'customer_email': customer.customer_email,
            'customer_address': customer.customer_address,
        })

    return JsonResponse({'customers': customer_data})


@login_required(login_url="/user/login/")
def save_customer(request):
    if request.method == 'POST':
        try:
            # Get the data from the request
            data = json.loads(request.body)

            customer_id = data.get('customer_id')
            customer_name = data.get('customer_name')
            customer_number = data.get('customer_number')
            customer_email = data.get('customer_email')
            customer_address = data.get('customer_address')

            # Check if the customer exists and update or create accordingly
            customer, created = Customer.objects.update_or_create(
                customer_id=customer_id,
                defaults={
                    'customer_name': customer_name,
                    'customer_contact': customer_number,
                    'customer_email': customer_email,
                    'customer_address': customer_address
                }
            )

            # Return success response
            return JsonResponse({'success': True})

        except Exception as e:
            # Return error response
            return JsonResponse({'success': False, 'error': str(e)})

    # Handle case where method is not POST
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required(login_url="/user/login/")
def retail_display(request,values=None):
    if values:
        try:
            # response = f"""<div class="h5 text-dark" style="text-align:left;white-space:pre-wrap;padding-right:50px;"><div class="p-2">{'SUB-TOTAL':<15}:     {round(request.session["Total"]-request.session["Tax_Total"],2)}</div><div class="p-2">{'TAX-TOTAL':<16}:     {request.session["Tax_Total"]}</div></div><hr><div class="h1 text-gray-900 pl-5">TOTAL : <span style="padding-left:80px;">{request.session["Total"]}</span></div>"""
            cart = request.session[settings.CART_SESSION_ID]
            
            if len(cart) == 0: return HttpResponse("IMAGE")
            
            total = round(pd.DataFrame(cart).T["line_total"].astype(float).sum(),2) 
            response = f"""<div class="card shadow-sm p-0 m-0" style="width:100%;height:95%">
                    <div class="card-header p-0" >
                        <table class="table p-0 m-0" style="text-align:right;">
                            <tr>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623); width:40%" >Barcode/Name</th>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623)">Qty</th>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623)">Price</th>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623)">L-Total<br>Tax</th>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623)">L-Total<br>Deposit</th>
                                <th style="font-family: bold;color:rgba(0, 0, 0, 0.623)">Line<br>Total</th>
                            </tr>
                        </table>
                    </div>
                    <div id="table-body" class="card-body" style="overflow: auto ;padding:0;">
                        <table class="table p-0 m-0" style="text-align:right;">
                """
            if cart:
                for key,value in cart.items():
                    response = response + f"""<tr>
                                <th style="text-align:left">{key} <br> {value['name']}</th> 
                                <td>{value['quantity']}</td>
                                <td>{value['price']}</td>
                                <td>{value['tax_value']}</td>
                                <td>{value['deposit_value']}</td>
                                <td>{value['line_total']}</td>
                            </tr> """
            response = response + f"""</table> </div> 
                                        <div class="card-footer py-3">
                                            <h1 class="m-0 font-weight-bold text-primary">Transaction Total:
                                            <span class="m-0 font-weight-bold text-dark" style="float:right;item-align:right">$ {total:.2f}</span>
                                            </h1>
                                        </div>
                                    </div>"""
            return HttpResponse(response)
        except Exception as e:
            print(e)
            return HttpResponse("")
    
    path="images4display/"  # insert the path to your directory   
    if os.path.exists(f"./{path}"):
        # print(f"{settings.STATIC_ROOT}/{path}")
        shutil.copytree(f"./{path}", f"{settings.STATIC_ROOT}/{path}", dirs_exist_ok=True)
    img_list = [ path+i for i in  os.listdir(path) if not i.endswith('.md')]
    
    return render(request,'retailDisplay.html',context={"store_name":settings.STORE_NAME, "display_images":img_list})


@login_required(login_url="/user/login/")
def report_regular(request,start_date,end_date):
    # timezone.localize(datetime.combine(datetime.strptime(start_date,"%Y-%m-%d").date(), datetime.min.time()))
    start_date = datetime.strptime(start_date,"%Y-%m-%d").date()
    end_date = datetime.strptime(end_date,"%Y-%m-%d").date()
    df = pd.DataFrame(productTransaction.objects.filter(transaction_date_time__date__range = (start_date,end_date)).order_by('-transaction_date_time').values())
    if not df.shape[0]:
        return redirect("/")

    df['transaction_date_time'] = df['transaction_date_time'].apply(lambda x: x.astimezone(tz) )
    df['date'] = df['transaction_date_time'].dt.date
    df['total_sales'] = (df['qty'] * df['sales_price']) + df['tax_amount'] + df['deposit_amount']
    df['total_pre_sales'] = df['qty'] * df['sales_price']

    date_group = df.groupby(['date','department','payment_type'])[['qty','total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
    table = date_group.reset_index().groupby(['date'])[['total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
    for i, val in table.iterrows():
        date_group.loc[(i," Day Total","")] = val
    table = date_group.reset_index().groupby(['date','department'])[['qty','total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
    for i, val in table.iterrows():
        if i[1] ==  " Day Total":
            continue
        date_group.loc[(i[0],i[1]," Department Total ")] = val

    date_group.loc[("TOTAL","TOTAL"," TOTAL")] = df[['total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
    for i, val in df.groupby('payment_type')[['total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum()).iterrows():
         date_group.loc[("TOTAL","TOTAL",i)] = val

    date_group = date_group.sort_index()
    date_group.fillna("",inplace=True)
    date_group.rename(columns = { 'qty':'Quantity','total_pre_sales':'Total Pre_Sales','tax_amount':'Total Tax',
            'deposit_amount':'Total Deposit','total_sales':'Total Sales'}, inplace = True)
    date_group.index.names = ['Date','Department','Payment Type',]

    return render(request,"reportsRegular.html", context={
            "table_html":date_group.to_html(classes= "table table-bordered table-hover h6 text-gray-900 border-5"),
            "start_date":start_date,"end_date":end_date,"store_name":settings.STORE_NAME,
            })


@login_required(login_url="/user/login/")
def dashboard_products(request):
    try:
        number = 10
        context = {}
        today_date=datetime.now().date()
        last_30_date = datetime.now().date() - timedelta(30)
        df = pd.DataFrame(productTransaction.objects.filter(transaction_date_time__date__range = (last_30_date,today_date)).order_by('-transaction_date_time').values())
        context['products_group'] = {}
        for i, df in df.groupby('department'):
            context['products_group'][i] = df.groupby(["barcode","name"])[["qty"]].sum().reset_index().sort_values(by=["qty"],ascending=False).iloc[:number].to_dict('records')

        context['low_inventory_products'] = product.objects.all().order_by('qty').values('barcode','name','qty')[:50]
        context['number'] = number
    except:
        return redirect("/register/")
    return render(request,"productsDashboard.html",context=context)


@login_required(login_url="/user/login/")
def dashboard_department(request):
    context ={}
    end_date=datetime.now().date()
    start_date=datetime.now().date()
    form = DateSelector(initial = {'end_date':end_date, 'start_date':start_date})
    if request.method == "POST":
        form = DateSelector(request.POST)
        if form.is_valid():
            end_date= form.cleaned_data['end_date']
            start_date= form.cleaned_data['start_date']
    df = pd.DataFrame(productTransaction.objects.filter(transaction_date_time__date__range = (start_date,end_date)).order_by('-transaction_date_time').values())
    if df.shape[0]:
        df['total_sales'] = (df['qty'] * df['sales_price']) + df['tax_amount'] + df['deposit_amount']
        df['total_pre_sales'] = df['qty'] * df['sales_price']
        sales_by_payment = df.groupby('payment_type')['total_sales'].sum()

        tableValues = [['Total QTY', 'Total Sales b4 Tax & Deposit', 'Total Tax', 'Total Deposit']+[f"Sales by {i}" for i in sales_by_payment.index.to_list()],
                            [df['qty'].sum(), df['total_pre_sales'].sum(), df['tax_amount'].sum(), df['deposit_amount'].sum() ]+sales_by_payment.to_list()]
        tableValues = [("TOTAL SALES",round(df['total_sales'].sum(),2))]+ list(zip(tableValues[0],tableValues[1]))
        table_fig = ff.create_table(tableValues, height_constant= 25,)
        table_fig.update_layout(margin = dict(b=10,t=0,l=0,r=0),height=275 ,)
        context['table_fig'] = po.plot(table_fig, auto_open=False, output_type='div',config= {'displayModeBar': False},include_plotlyjs=False)

        pie_fig = px.pie(values=sales_by_payment,names=sales_by_payment.index, color=sales_by_payment.index,
                            color_discrete_map={'CASH': "darkgreen",'UPI': "royalblue",'DEBIT/CREDIT':"darkslategray"} )
        pie_fig.update_layout(margin = dict(b=50,t=10,l=10,r=10),height=225 ,
                    title={ 'text': f"Date Period : ({start_date:%Y/%m/%d} - {end_date:%Y/%m/%d})", 'font_size':16,
                            'y':0.15, 'x':0.5,  'xanchor': 'center', 'yanchor': 'top'})
        pie_fig.update_traces(hovertemplate=None)
        context['pie_fig'] = po.plot(pie_fig, auto_open=False, output_type='div',config= {'displayModeBar': False},include_plotlyjs=False)

        sales_by_department = df.groupby(['department','payment_type'])[['qty','total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
        sales_by_department = sales_by_department.reset_index()

        bar_fig = px.bar(sales_by_department, x="department",  y="total_sales", color="payment_type",text_auto=True, hover_name="total_sales",
                hover_data={'qty':True,'total_pre_sales':True,'tax_amount':True,'deposit_amount':True,'total_sales':False,},
                labels={'qty':"Quantity",'payment_type':"Payment Type",'department':"Department",'total_sales':"Total Sales","total_pre_sales":"Total Sales b4 Tax & Deposit",
                        'tax_amount':"Total Tax Amount",'deposit_amount':"Total Deposit Amount"},
                color_discrete_map={  'CASH': "darkgreen",'UPI': "royalblue",'DEBIT/CREDIT':"darkslategray"})
        bar_fig.update_yaxes(title=f"Total Sales ({start_date:%Y/%m/%d} - {end_date:%Y/%m/%d})")
        bar_fig.update_layout(margin = dict(b=10,pad=0,t=10,l=10,r=10),height=500,showlegend=False)

        # df['date'] = df['transaction_date_time'].dt.date
        # date_group = df.groupby(['date','department','payment_type'])[['qty','total_pre_sales','tax_amount','deposit_amount','total_sales']].apply(lambda x : x.sum())
        # date_group = date_group.reset_index()
        # bar_fig = px.bar(date_group, x="date",  y="total_sales", facet_row="department", hover_name="total_sales", color="payment_type",
        #         hover_data={'qty':True,'total_pre_sales':True,'tax_amount':True,'deposit_amount':True,'total_sales':False,},
        #         labels={'qty':"Quantity",'payment_type':"Payment Type",'department':"Department",'total_sales':"Total Sales","total_pre_sales":"Total Sales b4 Tax & Deposit",
        #                 'tax_amount':"Total Tax Amount",'deposit_amount':"Total Deposit Amount",'date':"Date"},
        #          color_discrete_sequence=["darkgreen", "royalblue", "darkslategray"])
        # bar_fig.update_layout(margin = dict(b=10,pad=0,t=10,l=10,r=10),height=500,showlegend=False)

        context['bar_fig'] = po.plot(bar_fig, auto_open=False, output_type='div',config= {'displayModeBar': False},include_plotlyjs=False)

    context["report_link"] = f"/department_report/{start_date}/{end_date}/"
    context['form'] = form
    return render(request,"departmentDashboard.html",context=context)


@login_required(login_url="/user/login/")
def dashboard_sales(request):
    print("Dashboard view is loading...")  # Debugging message

    context = {}
    tz = pytz.timezone('US/Eastern')  # Adjust timezone as per your location

    # Ensure 'today_date' is timezone-aware and combine with time (00:00:00)
    today_date = datetime.combine(datetime.now().date(), datetime.min.time())
    today_date = tz.localize(today_date)  # Make it timezone-aware

    try:
        # Debugging: Check what today_date looks like
        print(f"today_date (timezone aware): {today_date}")

        # Fetch transactions and product transactions from the database
        transactions = transaction.objects.filter(date_time__gte=today_date)  # Using date_time instead of transaction_dt
        
        # Debugging: Check if transactions are returned
        print(f"Transactions query: {transactions}")
        print(f"Transactions count: {transactions.count()}")

        # Fetch product transactions (filtered by the date)
        productTransactions = productTransaction.objects.filter(transaction_date_time__date__gte=today_date.date())

        # Debugging: Check if any product transactions are returned
        print(f"Product Transactions query: {productTransactions}")
        print(f"Product Transactions count: {productTransactions.count()}")

        # Check if there are no transactions
        if not transactions.exists():
            print("No transactions found for the given date range.")  # Debugging message
            context['error'] = "No sales data available for the selected period."
            return render(request, "salesDashboard.html", context)

        # Process transactions data into DataFrame
        df = pd.DataFrame(transactions.values())
        if df.empty:
            print("DataFrame is empty.")  # Debugging message
            context['error'] = "No valid data found in the database."
            return render(request, "salesDashboard.html", context)

        # Debugging: Check the first few rows of the dataframe
        print(f"Processed transactions DataFrame:\n{df.head()}")

        # Apply timezone conversion to date_time and create 'date' column
        df['date_time'] = df['date_time'].apply(lambda x: x.astimezone(tz))  # Using date_time here instead of transaction_dt
        df['date'] = df['date_time'].dt.date  # Extract date part

        # Debugging: Print the first few rows to verify the data
        print(f"Processed transactions with 'date' column:\n{df.head()}")

        # Group by 'date' and sum the total sales
        df_date = df.groupby('date')['total_sale'].sum()
        df_date.index = pd.to_datetime(df_date.index)

        # Convert today_date.date() to pandas Timestamp for comparison
        today_date_ts = pd.Timestamp(today_date.date())  # Convert to pandas.Timestamp
        # Ensure missing keys are filled with zero (for today and beginning of the year)
        df_date[today_date_ts] = df_date.get(today_date_ts, 0)
        df_date = df_date.asfreq('D', fill_value=0)

        # Debugging: Print the sales data by date
        print(f"Sales data by date:\n{df_date.head()}")

        # Profit/Loss calculation for product transactions
        product_df = pd.DataFrame(productTransactions.values())
        if not product_df.empty:
            product_df['Profit_or_loss'] = (product_df['sales_price'] - product_df['cost_price']) * product_df['qty']
            product_df['date'] = product_df['transaction_date_time'].apply(lambda x: x.astimezone(tz).date())  # Use transaction_date_time here

            # Aggregate Profit/Loss by date
            profit_loss_by_date = product_df.groupby('date')['Profit_or_loss'].sum()
            total_profit_or_loss = profit_loss_by_date.sum()

            # Debugging: Print the profit/loss data
            print(f"Profit/Loss by date:\n{profit_loss_by_date.head()}")

            # Add profit information to context
            context['profit_today'] = profit_loss_by_date.get(today_date.date(), 0)
            context['profit_last_30_days'] = profit_loss_by_date[profit_loss_by_date.index > (today_date - timedelta(30)).date()].sum()
            context['profit_or_loss'] = total_profit_or_loss
        else:
            print("No product transactions found.")  # Debugging message
            context['profit_today'] = 0
            context['profit_last_30_days'] = 0
            context['profit_or_loss'] = 0

        # Populate context with sales data
        context['today_total_sales'] = df_date.get(today_date_ts, 0)
        context["add_info"] = {
            'Yesterday\'s Total Sales': df_date.get(today_date_ts - timedelta(1), 0),
            'Last 7 Days Avg Sales': df_date[df_date.index > today_date_ts - timedelta(7)].sum() / 7,
            '30 Days Avg Sales': df_date[df_date.index > today_date_ts - timedelta(30)].mean(),
            '30 Days Total Sales': df_date[df_date.index > today_date_ts - timedelta(30)].sum(),
            'WTD Total Sales': df_date.resample('W').sum()[-1] if len(df_date) > 7 else 0,
            'Last Week Total Sales': df_date.resample('W').sum()[-2] if len(df_date) > 14 else 0,
            'MTD Total Sales': df_date.resample('M').sum()[-1] if len(df_date) > 30 else 0,
            'YTD Total Sales': df_date.resample('Y').sum()[-1] if len(df_date) > 365 else 0,
        }

        # Debugging: Print the sales breakdown
        print(f"Sales breakdown info:\n{context['add_info']}")

        # Plotly: 30 Days Sales Chart
        fig = px.bar(
            x=df_date.index, y=df_date, text_auto=True, barmode='group', template="plotly_white",
            labels={"x": "Date", "y": "Total Sales"}
        )
        fig.update_xaxes(title="Days", tickformat='%a, %d/%m', tickangle=-90)
        fig.update_yaxes(title="Total Sales")
        fig.update_layout(margin=dict(b=10, pad=0, t=10, r=0, l=0))
        context['30_day_sales_graph'] = po.plot(fig, auto_open=False, output_type='div', config={'displayModeBar': False}, include_plotlyjs=True)

        # Plotly: Profit/Loss Chart
        if not product_df.empty:
            profit_loss_chart = px.bar(
                profit_loss_by_date.reset_index(), x='date', y='Profit_or_loss',
                labels={"date": "Date", "Profit_or_loss": "Profit/Loss ($)"}, title="Daily Profit/Loss"
            )
            profit_loss_chart.update_traces(
                marker_color = profit_loss_by_date.apply(lambda x: 'green' if x>0 else 'red')
            )
            profit_loss_chart.update_layout(margin=dict(b=10, pad=0, t=10))
            context['profit_loss_graph'] = po.plot(profit_loss_chart, auto_open=False, output_type='div', config={'displayModeBar': False}, include_plotlyjs=True)

        # Plotly: Payment Type Pie Chart for Today
        df_day_payment = df[df['date'] == today_date.date()].groupby('payment_type')['total_sale'].sum().reset_index()
        if not df_day_payment.empty:
            fig2 = px.pie(
                df_day_payment, values='total_sale', names='payment_type', template="plotly_white", height=195,
                labels={"payment_type": "Payment Type", "total_sale": "Total Sales"}
            )
            fig2.update_layout(margin=dict(b=10, pad=0, t=10))
            context['day_payment_graph'] = po.plot(fig2, auto_open=False, output_type='div', config={'displayModeBar': False}, include_plotlyjs=True)
        else:
            print("No payment data found for today.")  # Debugging message
            context['error'] = "No payment data available for today."

    except Exception as e:
        print(f"Error in dashboard_sales view: {e}")  # Debugging message
        context['error'] = f"An error occurred while generating the sales dashboard: {str(e)}"
        return render(request, "salesDashboard.html", context)

    return render(request, "salesDashboard.html", context)


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            request.session["Total"] = 0.00
            request.session["Tax_Total"] = 0.00
            return redirect('home')
        else:
            return render(request, 'registration/login.html',context={'error':True,"store_name":settings.STORE_NAME})
    else:
        return render(request, 'registration/login.html',context={"store_name":settings.STORE_NAME},)

# forgot password
def user_forgot_password(request):
    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                send_otp_email(user)
                return redirect('verify_otp', uidb64=user.id)
            except User.DoesNotExist:
                return render(request, 'registration/forgot_password.html', {'form': form, 'error': 'User not found'})
    else:
        form = EmailForm()
    return render(request, 'registration/forgot_password.html', {'form': form})


# generate and send otp to user's email address
def send_otp_email(user):
    """Send OTP email to the user."""
    otp = generate_otp()
    
    try:
        # Fetch the profile or create one if it doesn't exist
        profile = Profile.objects.get(user=user)
        # Update OTP and timestamp if profile exists
        profile.otp = otp
        profile.otp_timestamp = tz.localize(datetime.now())  # Ensure it's timezone-aware
        profile.save()
    except Profile.DoesNotExist:
        # Create a new profile if none exists
        Profile.objects.create(user=user, otp=otp, otp_timestamp=tz.localize(datetime.now()))
    
    subject = "Your OTP for Password Reset"
    message = f"Your OTP for password reset is {otp}. Please use it within the next 10 minutes."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


# generate 6 digit otp
def generate_otp():
    """Generate a random 6-digit OTP."""
    return ''.join(random.choices("0123456789", k=6))


# Verifies the otp entered by user is correct & is not expired
def verify_otp(request, uidb64):
    try:
        user = User.objects.get(id=uidb64)
        if request.method == "POST":
            otp_form = OTPForm(request.POST)
            if otp_form.is_valid():
                otp = otp_form.cleaned_data['otp']
                if user.profile.otp == otp and not user.profile.is_otp_expired():
                    # OTP is valid, let the user reset the password
                    return redirect('reset_password', uidb64=urlsafe_base64_encode(str(user.id).encode()))
                else:
                    return HttpResponse("Invalid OTP or OTP expired.")
        else:
            otp_form = OTPForm()
        return render(request, 'registration/verify_otp.html', {'form': otp_form})
    except User.DoesNotExist:
        return HttpResponse("User not found.")


# Allows to reset the password
def reset_password(request, uidb64):
    try:
        user = User.objects.get(id=urlsafe_base64_decode(uidb64).decode())
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        return render(request, 'registration/reset_password.html', {'form': form})
    except User.DoesNotExist:
        return HttpResponse("Invalid user.")

# display's message after password is reset
def password_reset_complete(request):
    # You can add any additional context here if needed.
    return render(request, 'registration/password_reset_complete.html')


@login_required(login_url="/user/login/")
def user_logout(request):
    logout(request)
    return render(request, 'registration/login.html',context={'logout':True})

