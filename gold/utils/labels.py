MONTH = {i:n for i,n in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}
def month(i): return MONTH.get(i,str(i))

DOW = {1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri"}
def dow(i):  return DOW.get(i,str(i))

def week(i): return f"W{i}"
