import ctypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

result = kernel32.GetActiveProcessorCount(0)
print("Active CPU cores:", result)