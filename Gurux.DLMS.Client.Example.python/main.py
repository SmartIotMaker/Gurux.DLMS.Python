#
#  --------------------------------------------------------------------------
#   Gurux Ltd
#
#
#
#  Filename: $HeadURL$
#
#  Version: $Revision$,
#                   $Date$
#                   $Author$
#
#  Copyright (c) Gurux Ltd
#
# ---------------------------------------------------------------------------
#
#   DESCRIPTION
#
#  This file is a part of Gurux Device Framework.
#
#  Gurux Device Framework is Open Source software; you can redistribute it
#  and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; version 2 of the License.
#  Gurux Device Framework is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  More information of Gurux products: http://www.gurux.org
#
#  This code is licensed under the GNU General Public License v2.
#  Full text may be retrieved at http://www.gnu.org/licenses/gpl-2.0.txt
# ---------------------------------------------------------------------------
import os
import sys
import traceback
import schedule
import threading
import time
import timedelta
import datetime
from gurux_serial import GXSerial
from gurux_net import GXNet
from gurux_dlms.enums import ObjectType
from gurux_dlms.objects.GXDLMSObjectCollection import GXDLMSObjectCollection
from GXSettings import GXSettings
from GXDLMSReader import GXDLMSReader
from gurux_dlms.GXDLMSClient import GXDLMSClient
from gurux_common.GXCommon import GXCommon
from gurux_dlms.enums.DataType import DataType
import locale
from gurux_dlms.GXDateTime import GXDateTime
from gurux_dlms.internal._GXCommon import _GXCommon
from gurux_dlms import GXDLMSException, GXDLMSExceptionResponse, GXDLMSConfirmedServiceError
from gurux_dlms.objects import GXDLMSProfileGeneric

try:
    import pkg_resources
    #pylint: disable=broad-except
except Exception:
    #It's OK if this fails.
    print("pkg_resources not found")

#pylint: disable=too-few-public-methods,broad-except
class ReadThread(threading.Thread):
    def __init__(self, threadname, devicexml, sap, setting, media):
        threading.Thread.__init__(self)
        self.threadname = threadname
        self.devicexml = devicexml
        self.sap = sap
        self.settings = setting
        self.media = media

    def run(self):
        reader = None
        try:
            # //////////////////////////////////////
            self.settings.setserverAddress(self.sap)

            reader = GXDLMSReader(self.settings.client, self.media, self.settings.trace, self.settings.invocationCounter, self.settings.iec)

            if self.settings.readObjects:
                read = False
                reader.initializeConnection()
                if self.settings.outputFile and os.path.exists(self.devicexml):
                    try:
                        c = GXDLMSObjectCollection.load(self.devicexml)
                        self.settings.client.objects.extend(c)
                        if self.settings.client.objects:
                            read = True
                    except Exception:
                        read = False
                if not read:
                    reader.getAssociationView()
                    reader.readScalerAndUnits()
                    reader.getProfileGenericColumns()
                    if self.settings.outputFile:
                        self.settings.client.objects.save(self.devicexml)
                for k, v in self.settings.readObjects:
                    obj = self.settings.client.objects.findByLN(ObjectType.NONE, k)
                    if obj is None:
                         raise Exception(self.threadname + ":Unknown logical name:" + k)
                    if isinstance(obj, GXDLMSProfileGeneric) and v == 2:
                        profileGenerics = self.settings.client.objects.getObjects(ObjectType.PROFILE_GENERIC)
                        for pg in profileGenerics:
                            if str(pg.name) == k:
                                end = datetime.datetime.now()
                                start = end - datetime.timedelta(seconds=7200)
                                val = reader.readRowsByRange(pg, start, end)
                    else:
                        val = reader.read(obj, v)
                    reader.showValue(v, val)
            else:
                reader.readAll(settings.outputFile)
        except (ValueError, GXDLMSException, GXDLMSExceptionResponse, GXDLMSConfirmedServiceError) as ex:
            print(ex)
        except (KeyboardInterrupt, SystemExit, Exception) as ex:
            traceback.print_exc()
            # settings.media.close()
            reader = None
        finally:
            if reader:
                try:
                    reader.close()
                except Exception:
                    # traceback.print_exc()
                    print(self.threadname + ":Ended. Press any key to continue.")

class sampleclient():
    @classmethod
    def main(cls, args):
        try:
            print("gurux_dlms version: " + pkg_resources.get_distribution("gurux_dlms").version)
            print("gurux_net version: " + pkg_resources.get_distribution("gurux_net").version)
            print("gurux_serial version: " + pkg_resources.get_distribution("gurux_serial").version)
        except Exception:
            #It's OK if this fails.
            print("pkg_resources not found")
        # args: the command line arguments
        settings1 = GXSettings()
        settings2 = GXSettings()

        # //////////////////////////////////////
        #  Handle command line parameters.
        ret = settings1.getParameters(args)
        if ret != 0:
            return

        ret = settings2.getParameters(args)
        if ret != 0:
            return
        # //////////////////////////////////////
        #  Initialize connection settings.
        if not isinstance(settings1.media, (GXSerial, GXNet)) and not isinstance(settings2.media, (GXSerial, GXNet)):
            raise Exception("Unknown media type.")
        while True:
            settings1.media.open()
            media1 = settings1.media

            thread1 = ReadThread("read-1704", "735999254300061704.xml", 4, settings1,media1)
            thread1.start()
            # time.sleep(1)
            thread2 = ReadThread("read-1703", "735999254300061703.xml", 5, settings2,media1)
            thread2.start()

            while True:
                if not thread1.isAlive() and not thread2.isAlive():
                # if not thread1.isAlive():
                    break;

            media1.close()
            time.sleep(10)

if __name__ == '__main__':
    sampleclient.main(sys.argv)
