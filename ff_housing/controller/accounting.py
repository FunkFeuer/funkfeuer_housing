from ff_housing import manager, model, db
from datetime import datetime, date
from dateutil.relativedelta import *
from dateutil.rrule import *

from ff_housing.utils import daysofmonth

def listcontracts():
    for c in model.Contract.query.filter_by(closed=False):
        bill_contract(c)
    



def bill_contract(c):
    if(c.needs_billing() == False):
        return False
    print("\n%s:" % c.billing_c)
    for package in c.packages:
        if package.needs_billing():
            amount = 0
            # next_billed - the span of this invoice element.
            next_billed = package.billed_until+relativedelta(months=+package.billing_period)
            if (next_billed <= date.today()):
                print ("!! something fishy here: package %s next_billed (%s) is in the past!" % (package, next_billed))
                continue
            
            # TODO: only bill until closed_date if closed_date
            
            # we iterate over a list of montly dates between billed_until and next_billed
            last_date = package.billed_until
            for next_date in list(rrule(MONTHLY, dtstart=package.billed_until, until=next_billed, bymonthday=package.billed_until.day)):
                next_date = next_date.date()
                if last_date == next_date:
                    continue;
                
                if (last_date.day == next_date.day):
                    # full month
                    amount += package.amount
                elif (int(next_date.month) != int(last_date.month)):
                    # days between two months
                    fraction_of_month = (daysofmonth(last_date) - last_date.day) / daysofmonth(last_date) + \
                        (next_date.day / daysofmonth(next_date))
                    amount += package.amount * fraction_of_month
                else:
                    # days in same month
                    fraction_of_month = (next_date.day - last_date.day) / daysofmonth(next_date)
                    amount += package.amount * fraction_of_month
                
                last_date = next_date
            
            
            print("\t%d * %s: %s - %s \t%f" % (package.quantity, package, package.billed_until, next_billed+relativedelta(days=-1), amount))
            
            # package.last_billed = date.today()
            # package.billed_until = next_billed

def bill_package(package):
    pass
