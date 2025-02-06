from AP33772 import AP33772

ap = AP33772()
ap.begin()
print(ap._num_pdo)
print(ap.read_current())
print(ap.read_voltage())
print(ap.read_temp())