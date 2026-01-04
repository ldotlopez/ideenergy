_BASE_URL = "https://www.i-de.es"
_REST_BASE_URL = f"{_BASE_URL}/consumidores/rest"

## End point used to login
# {
#     'redirect': 'informacion-del-contrato',
#     'zona': 'B',
#     'success': 'true',
#     'idioma': 'ES',
#     'uCcr': [140 hexadecimal data uppercas]
# }
_LOGIN_ENDPOINT = f"{_REST_BASE_URL}/loginNew/login/"

## End point used to renew session and get session limits
# On success (user logged):
# {
#     'total': '900',
#     'usSes': '12345678901X12',
#     'aviso': '15'
# }
# On failure (not logged):
# {
#     'usSes': ''
# }
_KEEP_SESSION = f"{_REST_BASE_URL}/loginNew/mantenerSesion/"

#
# URLs not confirmed since begining of the times
#

## Endpoint used for list contracts
# {
#     'success': true,
#     'contratos': [
#         {
#             'direccion': 'xxxxxxxxxxxxxxxxxxxxxxx',
#             'cups': 'ES0000000000000000AB',
#             'tipo': 'A',
#             'tipUsoEnergiaCorto': '-',
#             'tipUsoEnergiaLargo': '-',
#             'estContrato': 'Alta',
#             'codContrato': '123456789',
#             'esTelegestionado': True,
#             'presion': '1.00',
#             'fecUltActua': '01.01.1970',
#             'esTelemedido': False,
#             'tipSisLectura': 'TG',
#             'estadoAlta': True
#         }
#     ]
# }
_CONTRACTS_ENDPOINT = f"{_REST_BASE_URL}/cto/listaCtos/"

## Endpoint used to get contract details
# {
#     "ape1Titular": "xxxxxx                                       ",
#     "ape2Titular": "xxxxxx                                       ",
#     "codCliente": "12345678",
#     "codContrato": 123456789.0,
#     "codPoblacion": "000000",
#     "codProvincia": "00",
#     "codPostal": "00000",
#     "codSociedad": 3,
#     "codTarifaIblda": "92T0",
#     "codTension": "09",
#     "cups": "ES0000000000000000XY",
#     "direccion": "C/ XXXXXXXXXXXXXXXXXX, 12 , 34 00000-XXXXXXXXXXXXXXXXXXXX"
#         " - XXXXXXXXX           ",
#     "dni": "12345678Y",
#     "emailFactElec": "xxxxxxxxx@xxxxx.com",
#     "esAutoconsumidor": False,
#     "esAutogenerador": False,
#     "esPeajeDirecto": False,
#     "fecAltaContrato": "2000-01-01",
#     "fecBajaContrato": 1600000000000,
#     "fecUltActua": "22.10.2021",
#     "indEstadioPS": 4,
#     "indFraElectrn": "N",
#     "nomGestorOficina": "XXXXXXXXXXXX                                      ",
#     "nomPoblacion": "XXXXXXXXXXXXXXXXXXXX                         ",
#     "nomProvincia": "XXXXXXXXX                                    ",
#     "nomTitular": "XXXXX                                        ",
#     "numCtaBancaria": "0",
#     "numTelefono": "         ",
#     "numTelefonoAdicional": "123456789",
#     "potDia": 0.0,
#     "potMaxima": 5750,
#     "presion": "1.00",
#     "puntoSuministro": "1234567.0",
#     "tipAparato": "CN",
#     "tipCualificacion": "PP",
#     "tipEstadoContrato": "AL",
#     "tipo": "A",
#     "tipPuntoMedida": None,
#     "tipSectorEne": "01",
#     "tipSisLectura": "TG",
#     "tipSuministro": None,
#     "tipUsoEnerg": "",
#     "listContador": [
#         {
#             "fecInstalEquipo": "28-01-2011",
#             "propiedadEquipo": "i-DE",
#             "tipAparato": "CONTADOR TELEGESTION",
#             "tipMarca": "ZIV",
#             "numSerieEquipo": 12345678.0,
#         }
#     ],
#     "esTelegestionado": True,
#     "esTelegestionadoFacturado": True,
#     "esTelemedido": False,
#     "cau": None,
# }

_CONTRACT_DETAILS_ENDPOINT = f"{_REST_BASE_URL}/detalleCto/detalle/"
_CONTRACT_SELECTION_ENDPOINT = f"{_REST_BASE_URL}/cto/seleccion/"
_GENERATION_PERIOD_ENDPOINT = (
    f"{_REST_BASE_URL}/consumoNew/obtenerDatosGeneracionPeriodo/"
    "fechaInicio/{start:%d-%m-%Y}00:00:00/"
    "fechaFinal/{end:%d-%m-%Y}00:00:00/"
)

## Endpoint used to check ICP availability
# {
#     'icp': 'trueConectado'
# }
_ICP_STATUS_ENDPOINT = f"{_REST_BASE_URL}/rearmeICP/consultarEstado"

## Endpoint used to get current power demand
# {
#     "valMagnitud": "158.64",
#     "valInterruptor": "1",
#     "valEstado": "09",
#     "valLecturaContador": "43167",
#     "codSolicitudTGT": "012345678901",
# }
_MEASURE_ENDPOINT = f"{_REST_BASE_URL}/escenarioNew/obtenerMedicionOnline/24"

####
# URLs reviewed on 2023-06-22
####

_CONSUMPTION_PERIOD_ENDPOINT = (
    f"{_REST_BASE_URL}/consumoNew/obtenerDatosConsumoDH/"
    "{start:%d-%m-%Y}/"
    "{end:%d-%m-%Y}/"
    "horas/USU/"
)

## Endpoint used to get limits on the power demand query
# {
#     'resultado': 'correcto',
#     'fecMin': '01-03-202100:00:00',
#     'resultadoMensaje': '',
#     'fecMax': '30-11-202523:00:00'
# }
_POWER_DEMAND_LIMITS_ENDPOINT = (
    f"{_REST_BASE_URL}/consumoNew/obtenerLimitesFechasPotencia/"
)

## Endpoint used to get power demand history
# Must look something like this
# /consumoNew/obtenerPotenciasMaximasRangoV2/01-10-202400:00:00/01-11-202500:00:00
# /consumoNew/obtenerPotenciasMaximasRangoV2/01-03-202100:00:00/30-11-202523:00:00
# On error:
# {'resultado': 'error'}
_POWER_DEMAND_PERIOD_ENDPOINT = (
    f"{_REST_BASE_URL}/consumoNew/obtenerPotenciasMaximasRangoV2/"
    # fecMin and fecMax are provided by _POWER_DEMAND_LIMITS_ENDPOINT
    "{fecMin}/{fecMax}"
)
