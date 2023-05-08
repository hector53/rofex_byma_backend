import quickfix as fix
def config_fix_settings(SocketConnectPort, BeginString, SenderCompID, TargetCompID, id_fix):
    """
    ReconnectInterval=60
    FileLogPath=./Logs/ 
    FileStorePath=./Sessions/
    UseLocalTime=Y
    UseDataDictionary=Y
    AppDataDictionary=conf\spec\FIX50SP2_rofex.xml
    TransportDataDictionary=conf\spec\FIXT11.xml
    StartTime=00:00:00
    EndTime=00:00:00
    ValidateUserDefinedFields=N
    ResetOnLogon=Y
    ResetOnLogout=Y
    DefaultApplVerID=FIX.5.0SP2
    BeginString=FIXT.1.1
    SenderCompID=hectoracosta57626
    TargetCompID=BYMA
    SocketConnectHost=127.0.0.1
    SocketConnectPort=8080
    HeartBtInt=30
    TimeInForce=Day
    TradingSessionID=1
    ScreenLogShowIncoming=Y
    ScreenLogShowOutgoing=Y
    ScreenLogEvents=Y
    LogoutTimeout=5
    LogonTimeout=30
    ResetOnDisconnect=Y
    RefreshOnLogon=Y
    SocketNodelay=N
    ValidateFieldsHaveValues=N
    ValidateFieldsOutofOrder=N
    CheckLatency=N
    """
    settings =  fix.SessionSettings()
    defaultDic = fix.Dictionary()
    #aqui configuramos los string defaults para la configuracion de fix

    defaultDic.setBool("PersistMessages", True)
    defaultDic.setString("ConnectionType", "initiator")
    defaultDic.setString("ReconnectInterval", "60")
    defaultDic.setString("FileLogPath", "logs")
    defaultDic.setString("FileStorePath", "non")
    defaultDic.setBool("UseLocalTime", True)
    defaultDic.setBool("UseDataDictionary", True)
    defaultDic.setString("AppDataDictionary", "conf\spec\FIX50SP2_rofex.xml")
    defaultDic.setString("TransportDataDictionary", "conf\spec\FIXT11.xml")
    defaultDic.setString("StartTime", "00:00:00")
    defaultDic.setString("EndTime", "00:00:00")
    defaultDic.setBool("ValidateUserDefinedFields", False)
    defaultDic.setBool("ResetOnLogon", True)
    defaultDic.setBool("ResetOnLogout", True)
    defaultDic.setString("DefaultApplVerID", "FIX.5.0SP2")
    settings.set(defaultDic)
    dicSession = fix.Dictionary()

    #aqui configuramos los string para la sesion
    dicSession.setString("BeginString", str(BeginString))
    dicSession.setString("SenderCompID", str(SenderCompID))
    dicSession.setString("TargetCompID", str(TargetCompID))
    dicSession.setString("SocketConnectHost", "127.0.0.1")
    dicSession.setString("SocketConnectPort", str(SocketConnectPort))
    dicSession.setString("HeartBtInt", "30")
    dicSession.setString("TimeInForce", "Day")
    dicSession.setString("TradingSessionID", "1")
    dicSession.setBool("ScreenLogShowIncoming", True)
    dicSession.setBool("ScreenLogShowOutgoing", True)
    dicSession.setBool("ScreenLogEvents", True)
    dicSession.setString("LogoutTimeout", "5")
    dicSession.setString("LogonTimeout", "30")
    dicSession.setBool("ResetOnDisconnect", True)
    dicSession.setBool("RefreshOnLogon", True)
    dicSession.setBool("SocketNodelay", False)
    dicSession.setBool("ValidateFieldsHaveValues", False)
    dicSession.setBool("ValidateFieldsOutofOrder", False)
    dicSession.setBool("CheckLatency", False)
    sID = fix.SessionID(BeginString, SenderCompID, TargetCompID)
    settings.set(sID, dicSession)
    return settings