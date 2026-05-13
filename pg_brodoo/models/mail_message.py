from odoo import api, models

from ..services.project_chatter_queue_service import ProjectChatterQueueService
from ..services.project_mirror_sync_service import ProjectMirrorSyncService


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _get_pg_mirror_sync_service(self):
        return ProjectMirrorSyncService(self.env)

    def _pg_chatter_target_refs(self):
        refs = []
        for message in self:
            if message.model in {'project.project', 'project.task'} and message.res_id:
                refs.append((message.model, message.res_id))
        return refs

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        refs = messages._pg_chatter_target_refs()
        ProjectChatterQueueService(self.env).mark_dirty_from_refs(refs)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            messages._get_pg_mirror_sync_service().queue_from_refs(
                refs,
                trigger_type='message_create',
                trigger_model='mail.message',
                trigger_record_id=messages[:1].id or False,
            )
        return messages

    def write(self, vals):
        refs = self._pg_chatter_target_refs()
        result = super().write(vals)
        combined_refs = refs + self._pg_chatter_target_refs()
        ProjectChatterQueueService(self.env).mark_dirty_from_refs(combined_refs)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            self._get_pg_mirror_sync_service().queue_from_refs(
                combined_refs,
                trigger_type='message_write',
                trigger_model='mail.message',
                trigger_record_id=self[:1].id or False,
            )
        return result

    def unlink(self):
        refs = self._pg_chatter_target_refs()
        trigger_record_id = self[:1].id or False
        result = super().unlink()
        ProjectChatterQueueService(self.env).mark_dirty_from_refs(refs)
        if not self.env.context.get('pg_skip_mirror_sync_enqueue'):
            self._get_pg_mirror_sync_service().queue_from_refs(
                refs,
                trigger_type='message_unlink',
                trigger_model='mail.message',
                trigger_record_id=trigger_record_id,
            )
        return result
