/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

import { session } from "@web/session";

/**
 * AnalysisDashboard Component
 * This is the main landing page for the Analysis Management module.
 * It uses the OWL framework to provide a reactive, real-time cockpit.
 */
export class AnalysisDashboard extends Component {
    setup() {
        // Services used for navigation and data fetching
        this.action = useService("action");
        this.orm = useService("orm");
        this.user_id = session.uid;
        
        // Initialize reactive state for dashboard metrics
        this.state = useState({
            data: {
                kpis: {},
                pipeline: [],
                workload: [],
                risks: {},
                snapshot: { requirements: {}, deliverables: {} },
                my_work: {}
            },
            loading: true,
        });

        // OWL Lifecycle hook: Trigger data fetch before component is mounted
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("analysis.dashboard", "get_dashboard_data", []);
            if (data) {
                this.state.data = data;
            }
        } catch (error) {
            console.error("Dashboard failed to load data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    openView(resModel, domain, title) {
        this.action.doAction({
            name: title,
            type: "ir.actions.act_window",
            res_model: resModel,
            domain: domain,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openRequests(domain, title) { this.openView("analysis.request", domain, title); }
    openActionItems(domain, title) { this.openView("analysis.action.item", domain, title); }
    openDeliverables(domain, title) { this.openView("analysis.deliverable", domain, title); }
    openMeetings(domain, title) { this.openView("analysis.meeting", domain, title); }
    openRequirements(domain, title) { this.openView("analysis.requirement", domain, title); }
}

AnalysisDashboard.template = "analysis_management.AnalysisDashboard";

console.log("Analysis Management Dashboard JS Loading...");

// Explicitly register the client action
registry.category("actions").add("analysis_management.dashboard", AnalysisDashboard);

console.log("Analysis Management Dashboard Action Registered.");
