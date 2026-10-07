
def flood_stdout(count):
    for i in range(count):
        print "Line " + str(i) + ": " + ("x" * 100)
    return "completed"
