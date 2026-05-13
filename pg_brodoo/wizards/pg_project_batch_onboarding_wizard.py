import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PgProjectBatchOnboardingResult(models.TransientModel):
    _name = 'pg.project.batch.onboarding.result'
    _description = 'Resultado de Onboarding em Batch'

    wizard_id = fields.Many2one('pg.project.batch.onboarding.wizard', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Projeto', readonly=True)
    status = fields.Selection([
        ('success', 'Sucesso'),
        ('error', 'Erro'),
        ('skipped', 'Ignorado'),
    ], string='Estado', readonly=True)
    message = fields.Char(string='Mensagem', readonly=True)


class PgProjectBatchOnboardingWizard(models.TransientModel):
    _name = 'pg.project.batch.onboarding.wizard'
    _description = 'Onboarding em Batch — Mirror Inicial'

    state = fields.Selection([
        ('confirm', 'Confirmação'),
        ('done', 'Concluído'),
    ], default='confirm', readonly=True)

    eligible_project_ids = fields.Many2many(
        'project.project',
        'pg_batch_onboarding_eligible_rel',
        'wizard_id', 'project_id',
        string='Projetos Elegíveis',
        readonly=True,
    )
    ineligible_project_ids = fields.Many2many(
        'project.project',
        'pg_batch_onboarding_ineligible_rel',
        'wizard_id', 'project_id',
        string='Projetos Sem Repositório/Branch',
        readonly=True,
    )
    eligible_count = fields.Integer(readonly=True)
    ineligible_count = fields.Integer(readonly=True)

    result_line_ids = fields.One2many(
        'pg.project.batch.onboarding.result',
        'wizard_id',
        string='Resultados',
        readonly=True,
    )
    success_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        project_ids = self.env.context.get('default_project_ids') or []
        if project_ids:
            projects = self.env['project.project'].browse(project_ids).exists()
            eligible = projects.filtered(
                lambda p: p.pg_repository_id and (p.pg_repo_branch or '').strip()
            )
            ineligible = projects - eligible
            vals.update({
                'eligible_project_ids': [(6, 0, eligible.ids)],
                'ineligible_project_ids': [(6, 0, ineligible.ids)],
                'eligible_count': len(eligible),
                'ineligible_count': len(ineligible),
            })
        return vals

    def action_run_batch_onboarding(self):
        self.ensure_one()
        results = []
        success = error = skipped = 0

        for project in self.eligible_project_ids:
            try:
                # Garante que o scope sync está ativo — necessário para _is_pg_mirror_sync_enabled()
                sync_activated = False
                if not project.pg_scope_sync_enabled and not project.pg_status_sync_enabled:
                    project.with_context(pg_skip_scope_sync_enqueue=True).sudo().write({
                        'pg_scope_sync_enabled': True,
                    })
                    sync_activated = True

                service = project._get_pg_mirror_sync_service()
                run = service.queue_project(
                    project,
                    trigger_type='manual',
                    trigger_model='project.project',
                    trigger_record_id=project.id,
                )
                if run and run.status == 'queued':
                    service.process_run(run)
                    msg = _('Mirror publicado com sucesso. Scope sync ativado automaticamente.') if sync_activated else _('Mirror publicado com sucesso.')
                    results.append({
                        'wizard_id': self.id,
                        'project_id': project.id,
                        'status': 'success',
                        'message': msg,
                    })
                    success += 1
                elif run:
                    results.append({
                        'wizard_id': self.id,
                        'project_id': project.id,
                        'status': 'skipped',
                        'message': _('Sync já em curso para este projeto.'),
                    })
                    skipped += 1
                else:
                    results.append({
                        'wizard_id': self.id,
                        'project_id': project.id,
                        'status': 'skipped',
                        'message': _('Mirror sync não disponível neste projeto.'),
                    })
                    skipped += 1
            except Exception as e:
                _logger.exception('Erro no batch onboarding — projeto %s (id=%s)', project.name, project.id)
                results.append({
                    'wizard_id': self.id,
                    'project_id': project.id,
                    'status': 'error',
                    'message': str(e)[:250],
                })
                error += 1

        for project in self.ineligible_project_ids:
            results.append({
                'wizard_id': self.id,
                'project_id': project.id,
                'status': 'skipped',
                'message': _('Repositório ou branch não configurados.'),
            })
            skipped += 1

        self.env['pg.project.batch.onboarding.result'].create(results)
        self.write({
            'state': 'done',
            'success_count': success,
            'error_count': error,
            'skipped_count': skipped,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
