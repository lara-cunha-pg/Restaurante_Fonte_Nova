from odoo import api, models

from ..services.project_mirror_sync_service import ProjectMirrorSyncService


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_pg_mirror_sync_service(self):
        return ProjectMirrorSyncService(self.env)

    def _pg_mirror_target_refs(self):
        refs = []
        message_records = self.env['mail.message']
        for attachment in self:
            if attachment.res_model in {'project.project', 'project.task'} and attachment.res_id:
                refs.append((attachment.res_model, attachment.res_id))
                continue
            if attachment.res_model == 'mail.message' and attachment.res_id:
                message_records |= self.env['mail.message'].browse(attachment.res_id).exists()
        if message_records:
            refs.extend(message_records._pg_chatter_target_refs())
        return refs

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            attachments._get_pg_mirror_sync_service().queue_from_refs(
                attachments._pg_mirror_target_refs(),
                trigger_type='attachment_create',
                trigger_model='ir.attachment',
                trigger_record_id=attachments[:1].id or False,
            )
        return attachments

    def write(self, vals):
        refs = self._pg_mirror_target_refs()
        result = super().write(vals)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            self._get_pg_mirror_sync_service().queue_from_refs(
                refs + self._pg_mirror_target_refs(),
                trigger_type='attachment_write',
                trigger_model='ir.attachment',
                trigger_record_id=self[:1].id or False,
            )
        return result

    def unlink(self):
        refs = self._pg_mirror_target_refs()
        trigger_record_id = self[:1].id or False
        result = super().unlink()
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            self._get_pg_mirror_sync_service().queue_from_refs(
                refs,
                trigger_type='attachment_unlink',
                trigger_model='ir.attachment',
                trigger_record_id=trigger_record_id,
            )
        return result
