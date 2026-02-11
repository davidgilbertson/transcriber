import pythoncom
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

def test():
    pythoncom.CoInitialize()
    try:
        device = AudioUtilities.GetSpeakers()
        print(f"Device type: {type(device)}")
        print(f"Device attributes: {dir(device)}")
        
        try:
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            print("Successfully called Activate")
        except AttributeError as e:
            print(f"Caught expected AttributeError: {e}")
            
        if hasattr(device, 'EndpointVolume'):
            print("Device has EndpointVolume attribute")
            ev = device.EndpointVolume
            print(f"EndpointVolume type: {type(ev)}")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    test()
