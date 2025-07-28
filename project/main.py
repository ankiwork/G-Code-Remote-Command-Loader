from project.station.controllers.station import Station

xui = Station()
xui.move_to_home()  # $H
xui.move_to_coordinates(100, 100, 0)
xui.move_to_coordinates(50, 20, 2)
