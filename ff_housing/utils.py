from . import model
from calendar import monthrange

def daysofmonth(date):
    return(monthrange(date.year, date.month)[1]) 

def ip_find_server(ip):
    ''' find server to IP (without subnet)'''
    ip = model.IP.query.filter(model.IP.ip_address.like(ip+"/_%")).first()
    return ip.server if ip else None
