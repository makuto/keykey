import mido


def chooseDevice(devices, searchString):
    matchingDevice = None
    for device in devices:
        if searchString.lower() in device.lower():
            matchingDevice = device
    return matchingDevice


def openOut(deviceName):
    outputPort = chooseDevice(mido.get_output_names(), deviceName)
    if outputPort:
        return mido.open_output(outputPort)
    else:
        return None


def openIn(deviceName):
    inputPort = chooseDevice(mido.get_input_names(), deviceName)
    if inputPort:
        return mido.open_input(inputPort)
    else: 
        return None