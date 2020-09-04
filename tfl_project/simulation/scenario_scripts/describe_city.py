from tfl_project.simulation.city import City


def describe_city(city: City):
    """Takes a city and describes the number of bikes and docks. Ideally this should be a method in City"""
    docks = sum([s._capacity for s in city.stations.values()])
    bikes = sum([s._docked for s in city.stations.values()])
    warehouse_docks = sum([w._capacity for w in city.warehouses.values()])
    warehouse_bikes = sum([w._docked for w in city.warehouses.values()])
    print(
        f"""
city has a total of {bikes+warehouse_bikes} bikes:
    {bikes} docked at stations
    {warehouse_bikes} stored in warehouses
and a total of {docks+warehouse_docks} docks:
    {docks} in stations
    {warehouse_docks} in warehouses
station normalised availability: {bikes/docks: .2f}
total normalised availability: {(bikes+warehouse_bikes)/(docks+warehouse_docks): .2f}
The largest station had {max([s._capacity for s in city.stations.values()])} docks""")
