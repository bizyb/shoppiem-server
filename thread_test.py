from concurrent.futures import ThreadPoolExecutor

def print_x():
    try:
        print x # needs to raise an exception
    except Exception:
        print "caught an exception in child thread!!" 

with ThreadPoolExecutor(max_workers=1) as executor:
    try:
        executor.submit(print_x)
        print "submitted work; waiting for exception......"
    except Exception:
        print "Exception raised in child thread!!!!!"
    