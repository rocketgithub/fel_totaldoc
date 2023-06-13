# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

from datetime import datetime
import base64
from lxml import etree
import requests

import html
import uuid

import logging

class AccountMove(models.Model):
    _inherit = "account.move"

    pdf_fel = fields.Char('PDF FEL', copy=False)

    def _post(self, soft=True):
        if self.certificar():
            return super(AccountMove, self)._post(soft)
        
    def post(self):
        if self.certificar():
            return super(AccountMove, self).post()

    def certificar(self):
        for factura in self:
            if factura.requiere_certificacion('totaldoc'):
                self.ensure_one()
                
                if factura.error_pre_validacion():
                    return
                
                dte = factura.dte_documento()
                xmls = etree.tostring(dte, encoding="UTF-8")
                logging.warning(xmls)
                xmls_base64 = base64.b64encode(xmls)
                logging.warning(xmls_base64)

                request_url = "https://ingestor-dev.totaldoc.io/v1.0"
                if factura.company_id.pruebas_fel:
                    request_url = "https://ingestor-dev.totaldoc.io/v1.0"
                
                headers = { "Content-Type": "application/json", "apiKey": factura.company_id.apikey_fel }
                data = { "dte": { "nit_transmitter": factura.company_id.vat.replace('-',''), "xml_dte": xmls_base64.decode("utf-8") } }
                logging.warning(data)
                r = requests.post(request_url+"/signature", json=data, headers=headers)
                logging.warning(r.text)
                resultado = r.json()

                if resultado["xmlSigned"]:
                    headers = { "Content-Type": "application/json", "apiKey": factura.company_id.apikey_fel }
                    data = { "dte": { "nit_transmitter": factura.company_id.vat.replace('-',''), "serie": factura.journal_id.code, "number": factura.id, "xml_dte": resultado["xmlSigned"] } }
                    r = requests.post(request_url+"/dte", json
                    
                    =data, headers=headers)
                    logging.warning(r.text)
                    resultado = r.json()

                    if "status" in resultado and resultado["status"] in ["ok", "test"]:
                        factura.firma_fel = resultado["uuid"]
                        factura.serie_fel = resultado["serie"]
                        factura.numero_fel = resultado["number"]
                        factura.documento_xml_fel = xmls_base64
                        factura.resultado_xml_fel = resultado["xmlSigned"]
                        factura.pdf_fel = "https://print.totaldoc.io/pdf?uuid="+resultado["uuid"]
                        if factura.company_id.pruebas_fel:
                            factura.pdf_fel = "https://print-dev.totaldoc.io/pdf?uuid="+resultado["uuid"]
                        factura.certificador_fel = "totaldoc"
                    else:
                        factura.error_certificador(r.text)
                        return False
                        
                else:
                    factura.error_certificador(r.text)
                    return False

        return True
    
    def button_cancel(self):
        result = super(AccountMove, self).button_cancel()
        for factura in self:
            if factura.requiere_certificacion() and factura.firma_fel:
                dte = factura.dte_anulacion()
                xmls = etree.tostring(dte, encoding="UTF-8")
                logging.warning(xmls)
                xmls_base64 = base64.b64encode(xmls)

                request_url = "https://ingestor-dev.totaldoc.io/v1.0"
                if factura.company_id.pruebas_fel:
                    request_url = "https://ingestor-dev.totaldoc.io/v1.0"

                headers = { "Content-Type": "application/json", "apiKey": factura.company_id.apikey_fel }
                data = { "dte": { "nit_transmitter": factura.company_id.vat.replace('-',''), "xml_dte": xmls_base64.decode("utf-8") } }
                r = requests.post(request_url+"/signanulacion", json=data, headers=headers)
                logging.warning(r.text)
                resultado = r.json()

                if resultado["xmlSigned"]:
                    headers = { "Content-Type": "application/json", "apiKey": factura.company_id.apikey_fel }
                    data = { "dte": { "nit_transmitter": factura.company_id.vat.replace('-',''), "serie": factura.journal_id.code, "number": factura.id, "xml_dte": resultado["xmlSigned"] } }
                    r = requests.post(request_url+"/dte-anulacion", json=data, headers=headers)
                    logging.warning(r.text)
                    resultado = r.json()

                    if "status" not in resultado or resultado["status"] not in ["ok", "test"]:
                        raise UserError(r.text)
                else:
                    raise UserError(r.text)
                    
        return result
                
class AccountJournal(models.Model):
    _inherit = "account.journal"

    generar_fel = fields.Boolean('Generar FEL',)

class ResCompany(models.Model):
    _inherit = "res.company"

    apikey_fel = fields.Char('apiKey FEL')
    pruebas_fel = fields.Boolean('Modo de Pruebas FEL')
    
