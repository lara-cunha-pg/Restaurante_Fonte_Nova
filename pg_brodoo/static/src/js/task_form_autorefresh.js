/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

const PG_AI_REFRESH_INTERVAL_MS = 4000;

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        this.pgAiRefreshIntervalId = null;
        this.pgAiRefreshPending = false;

        const shouldAutoRefresh = () => {
            const root = this.model?.root;
            const aiStatus = root?.data?.ai_status;
            return (
                this.props.resModel === "project.task" &&
                !!root?.resId &&
                !root.dirty &&
                ["queued", "running"].includes(aiStatus)
            );
        };

        const refreshTask = async () => {
            if (this.pgAiRefreshPending || !shouldAutoRefresh()) {
                return;
            }

            this.pgAiRefreshPending = true;
            try {
                const { resId, resIds } = this.model.root;
                await this.model.load({ resId, resIds });
            } finally {
                this.pgAiRefreshPending = false;
            }
        };

        onMounted(() => {
            refreshTask();
            this.pgAiRefreshIntervalId = window.setInterval(refreshTask, PG_AI_REFRESH_INTERVAL_MS);
        });

        onWillUnmount(() => {
            if (this.pgAiRefreshIntervalId) {
                window.clearInterval(this.pgAiRefreshIntervalId);
                this.pgAiRefreshIntervalId = null;
            }
        });
    },
});
