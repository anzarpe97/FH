from odoo import _, fields, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    remote_sync_state = fields.Selection(
        selection=[("draft", "Sin enviar"), ("sent", "Enviado"), ("failed", "Fallido")],
        string="Estado Envío Remoto",
        default="draft",
        readonly=True,
    )
    remote_sync_date = fields.Datetime(string="Último Envío Remoto", readonly=True)
    remote_sync_message = fields.Char(string="Mensaje Envío Remoto", readonly=True)

    def _get_remote_connection(self):
        connection_model = self.env["odoo.remote.connection"].sudo()
        connections = connection_model.search([("active", "=", True)], order="id desc")
        connection = connections.filtered(lambda c: c.state == "connected")[:1] or connections[:1]
        if not connection:
            raise UserError(_("No hay conexiones configuradas. Crea una en Conector Odoo > Conexiones."))
        return connection

    def action_send_to_remote(self):
        for session in self:
            connection = session._get_remote_connection()
            try:
                _session_sent, order_sent, line_sent, payment_sent, stock_move_sent = connection.send_pos_sessions(session)
                session.write(
                    {
                        "remote_sync_state": "sent",
                        "remote_sync_date": fields.Datetime.now(),
                        "remote_sync_message": _(
                            "Sesión enviada. Pedidos: %(orders)s | Líneas: %(lines)s | Pagos: %(payments)s | Recogidas: %(moves)s.",
                            orders=order_sent,
                            lines=line_sent,
                            payments=payment_sent,
                            moves=stock_move_sent,
                        ),
                    }
                )
            except Exception as error:
                session.write(
                    {
                        "remote_sync_state": "failed",
                        "remote_sync_date": fields.Datetime.now(),
                        "remote_sync_message": str(error),
                    }
                )
                raise UserError(_("No fue posible enviar la sesión %(session)s: %(error)s", session=session.name, error=error)) from error

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío POS completado"),
                "message": _(
                    "Se enviaron %(sessions)s sesiones, %(orders)s pedidos, %(lines)s líneas, %(payments)s pagos y %(moves)s recogidas.",
                    sessions=len(self),
                    orders=sum(len(session.order_ids) for session in self),
                    lines=sum(len(session.order_ids.mapped("lines")) for session in self),
                    payments=sum(len(session.order_ids.mapped("payment_ids")) for session in self),
                    moves=sum(len(session.order_ids.mapped("picking_ids.move_ids_without_package")) for session in self),
                ),
                "type": "success",
                "sticky": False,
            },
        }
