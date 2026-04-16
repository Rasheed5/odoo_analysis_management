/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

/**
 * AnalysisDashboard Component
 * Main landing page for the Analysis Management module.
 * Uses OWL framework to provide a reactive, real-time cockpit.
 */
export class AnalysisDashboard extends Component {
    setup() {
        // Services used for navigation and data fetching
        this.action = useService("action");
        this.orm = useService("orm");

        // Refs for Charts
        this.typeChartRef = useRef("typeChart");
        this.velocityChartRef = useRef("velocityChart");
        this.charts = []; // Track chart instances for cleanup

        // Initialize reactive state for dashboard metrics
        this.state = useState({
            data: {
                kpis: { open_requests: 0, overdue_requests: 0, pending_review_deliverables: 0, meetings_today: 0 },
                pipeline: [],
                workload: [],
                risks: { today_blockers: 0, waiting_requests: 0, escalated_actions: 0 },
                snapshot: { requirements: {}, deliverables: {} },
                my_work: { requests: 0, actions: 0, deliverables: 0, meetings: 0 },
                change_requests: { total_open: 0, pending_impact: 0, pending_approval: 0, total_cost: 0 },
                domains: {},
                charts: {
                    type_distribution: { labels: [], data: [] },
                    monthly_velocity: { labels: [], data: [] }
                },
            },
            loading: true,
        });

        // OWL Lifecycle hook: Trigger data fetch before component is mounted
        onWillStart(async () => {
            await this.loadDashboardData();
        });

        // Render charts after component is mounted and data is available
        onMounted(async () => {
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (_e) {
                // Chart.js may already be loaded or path differs — ignore and try rendering
            }
            this.renderCharts();
        });

        // Cleanup chart instances to avoid memory leaks
        onWillUnmount(() => {
            this.charts.forEach(chart => chart.destroy());
        });
    }

    renderCharts() {
        if (!this.state.data.charts) return;
        if (typeof Chart === "undefined") {
            console.warn("Dashboard: Chart.js not available, skipping chart rendering.");
            return;
        }

        // Ensure we don't double-render if already initialized
        this.charts.forEach(chart => chart.destroy());
        this.charts = [];

        // 1. Request Type Distribution (Doughnut Chart)
        const typeCtx = this.typeChartRef.el;
        if (typeCtx) {
            const chart = new Chart(typeCtx, {
                type: 'doughnut',
                data: {
                    labels: this.state.data.charts.type_distribution.labels,
                    datasets: [{
                        data: this.state.data.charts.type_distribution.data,
                        backgroundColor: [
                            '#007bff', '#28a745', '#ffc107', '#dc3545',
                            '#6f42c1', '#e83e8c', '#fd7e14', '#20c997',
                            '#17a2b8', '#6610f2'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            this.charts.push(chart);
        }

        // 2. Monthly Velocity (Bar Chart)
        const velocityCtx = this.velocityChartRef.el;
        if (velocityCtx) {
            const chart = new Chart(velocityCtx, {
                type: 'bar',
                data: {
                    labels: this.state.data.charts.monthly_velocity.labels,
                    datasets: [{
                        label: 'Requests Created',
                        data: this.state.data.charts.monthly_velocity.data,
                        backgroundColor: 'rgba(0, 123, 255, 0.7)',
                        borderColor: '#007bff',
                        borderWidth: 1,
                        borderRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
            this.charts.push(chart);
        }
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("analysis.dashboard", "get_dashboard_data", []);
            if (data) {
                this.state.data = data;
                // Safe fallback for financial total if backend returns null/undefined
                if (!this.state.data.change_requests) {
                    this.state.data.change_requests = { total_open: 0, pending_impact: 0, pending_approval: 0, total_cost: 0 };
                }
                if (this.state.data.change_requests.total_cost == null) {
                    this.state.data.change_requests.total_cost = 0;
                }
            } else {
                console.warn("Dashboard: Backend returned no data.");
            }
        } catch (error) {
            console.error("Dashboard CRITICAL ERROR: Failed to load data from backend.", error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Failsafe Domain Sanitizer:
     * Ensures all domain conditions are valid types before passing to Odoo's SearchModel.
     */
    _sanitizeDomain(domain) {
        if (!Array.isArray(domain)) return domain;
        return domain.map(condition => {
            if (Array.isArray(condition)) {
                return condition.map(val => (val === undefined || val === null) ? 0 : val);
            }
            return condition;
        });
    }

    openView(resModel, domain, title) {
        this.action.doAction({
            name: title,
            type: "ir.actions.act_window",
            res_model: resModel,
            domain: this._sanitizeDomain(domain),
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
    openChangeRequests(domain, title) { this.openView("analysis.change.request", domain, title); }
}

AnalysisDashboard.template = "analysis_management.AnalysisDashboard";

// Explicitly register the client action
registry.category("actions").add("analysis_management.dashboard", AnalysisDashboard);
