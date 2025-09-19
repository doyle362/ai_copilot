/**
 * Level Analyst Web Component
 *
 * Usage:
 * <level-analyst-card
 *   token="your-jwt-token"
 *   location-id="uuid"
 *   zone-id="z-110"
 *   mode="review|approve|execute"
 *   api-url="http://localhost:8088">
 * </level-analyst-card>
 */

class LevelAnalystCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.apiClient = null;
    this.data = {
      insights: [],
      recommendations: [],
      priceChanges: [],
      loading: true,
      error: null
    };
  }

  connectedCallback() {
    this.render();
    this.initializeApiClient();
    this.loadData();
  }

  static get observedAttributes() {
    return ['token', 'location-id', 'zone-id', 'mode', 'api-url'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.initializeApiClient();
      if (name !== 'mode') {
        this.loadData();
      }
    }
  }

  get token() {
    return this.getAttribute('token');
  }

  get locationId() {
    return this.getAttribute('location-id');
  }

  get zoneId() {
    return this.getAttribute('zone-id');
  }

  get mode() {
    return this.getAttribute('mode') || 'review';
  }

  get apiUrl() {
    return this.getAttribute('api-url') || 'http://localhost:8088';
  }

  initializeApiClient() {
    this.apiClient = new AnalystApiClient(this.apiUrl, this.token);
  }

  async loadData() {
    if (!this.apiClient || !this.token) return;

    this.data.loading = true;
    this.data.error = null;
    this.render();

    try {
      const [insightsRes, recsRes, changesRes] = await Promise.all([
        this.apiClient.getInsights(this.zoneId),
        this.apiClient.getRecommendations(this.zoneId),
        this.apiClient.getPriceChanges(this.zoneId),
      ]);

      this.data.insights = insightsRes.success ? (insightsRes.data?.insights || []) : [];
      this.data.recommendations = recsRes.success ? (recsRes.data?.recommendations || []) : [];
      this.data.priceChanges = changesRes.success ? (changesRes.data?.changes || []) : [];

      const hasErrors = [insightsRes, recsRes, changesRes].some(res => !res.success);
      if (hasErrors) {
        const errorMessages = [insightsRes, recsRes, changesRes]
          .filter(res => !res.success)
          .map(res => res.error)
          .join('; ');
        this.data.error = errorMessages;
      }
    } catch (error) {
      this.data.error = 'Failed to load data from API';
      console.error('Load data error:', error);
    }

    this.data.loading = false;
    this.render();
  }

  async generateRecommendations() {
    if (!this.apiClient) return;

    this.data.loading = true;
    this.render();

    try {
      const response = await this.apiClient.generateRecommendations(this.zoneId);
      if (response.success) {
        // Reload data after a delay to allow for background processing
        setTimeout(() => {
          this.loadData();
        }, 2000);

        // Emit custom event
        this.dispatchEvent(new CustomEvent('recommendationsRequested', {
          detail: { zoneId: this.zoneId },
          bubbles: true
        }));
      } else {
        this.data.error = response.error || 'Failed to generate recommendations';
        this.data.loading = false;
        this.render();
      }
    } catch (error) {
      this.data.error = 'Failed to generate recommendations';
      this.data.loading = false;
      this.render();
    }
  }

  async applyChange(changeId) {
    if (!this.apiClient) return;

    try {
      const response = await this.apiClient.applyPriceChange(changeId);
      if (response.success) {
        this.loadData(); // Reload to get updated status

        // Emit custom event
        this.dispatchEvent(new CustomEvent('applyRequest', {
          detail: { changeId, zoneId: this.zoneId },
          bubbles: true
        }));
      } else {
        this.data.error = response.error || 'Failed to apply change';
        this.render();
      }
    } catch (error) {
      this.data.error = 'Failed to apply change';
      this.render();
    }
  }

  render() {
    const { insights, recommendations, priceChanges, loading, error } = this.data;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .analyst-card {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          background: white;
          overflow: hidden;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .header {
          padding: 16px;
          background: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .title {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .title h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
        }

        .title p {
          margin: 0;
          font-size: 14px;
          color: #6b7280;
        }

        .actions {
          display: flex;
          gap: 8px;
        }

        .btn {
          padding: 8px 16px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: white;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn:hover {
          background: #f3f4f6;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-primary {
          background: #2563eb;
          border-color: #2563eb;
          color: white;
        }

        .btn-primary:hover {
          background: #1d4ed8;
        }

        .error {
          padding: 12px 16px;
          background: #fef2f2;
          border-left: 4px solid #ef4444;
          color: #991b1b;
          font-size: 14px;
        }

        .loading {
          padding: 40px;
          text-align: center;
          color: #6b7280;
        }

        .content {
          padding: 16px;
        }

        .tabs {
          display: flex;
          border-bottom: 1px solid #e5e7eb;
          margin: -16px -16px 16px -16px;
        }

        .tab {
          padding: 12px 16px;
          border: none;
          background: none;
          cursor: pointer;
          font-size: 14px;
          color: #6b7280;
          border-bottom: 2px solid transparent;
          transition: all 0.2s;
        }

        .tab:hover {
          color: #374151;
        }

        .tab.active {
          color: #2563eb;
          border-bottom-color: #2563eb;
        }

        .tab-badge {
          background: #e5e7eb;
          color: #374151;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 12px;
          margin-left: 8px;
        }

        .tab.active .tab-badge {
          background: #2563eb;
          color: white;
        }

        .item {
          padding: 12px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          margin-bottom: 12px;
          background: #fafafa;
        }

        .item:last-child {
          margin-bottom: 0;
        }

        .item-header {
          display: flex;
          justify-content: between;
          align-items: start;
          margin-bottom: 8px;
        }

        .item-title {
          font-weight: 500;
          color: #111827;
          margin: 0 0 4px 0;
        }

        .item-text {
          color: #6b7280;
          font-size: 14px;
          line-height: 1.5;
          margin: 0;
        }

        .item-meta {
          font-size: 12px;
          color: #9ca3af;
          margin-top: 8px;
        }

        .status {
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-pending {
          background: #fef3c7;
          color: #d97706;
        }

        .status-applied {
          background: #d1fae5;
          color: #065f46;
        }

        .status-draft {
          background: #e5e7eb;
          color: #374151;
        }

        .empty-state {
          text-align: center;
          padding: 40px 16px;
          color: #6b7280;
        }

        .empty-state h4 {
          margin: 0 0 8px 0;
          color: #111827;
        }

        .empty-state p {
          margin: 0;
          font-size: 14px;
        }

        .price-change {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;
        }

        .price-increase {
          color: #059669;
        }

        .price-decrease {
          color: #dc2626;
        }

        .change-actions {
          display: flex;
          gap: 4px;
          margin-top: 8px;
        }

        .btn-sm {
          padding: 4px 8px;
          font-size: 12px;
          border-radius: 4px;
        }

        .btn-success {
          background: #059669;
          border-color: #059669;
          color: white;
        }

        .btn-danger {
          background: #dc2626;
          border-color: #dc2626;
          color: white;
        }
      </style>

      <div class="analyst-card">
        <div class="header">
          <div class="title">
            <div>
              <h3>🧠 Level Analyst</h3>
              <p>Zone: ${this.zoneId || 'N/A'} • Mode: ${this.mode}</p>
            </div>
          </div>
          <div class="actions">
            <button class="btn" onclick="window.location.reload()" ${loading ? 'disabled' : ''}>
              🔄 Refresh
            </button>
            <button class="btn btn-primary" id="generate-btn" ${loading ? 'disabled' : ''}>
              📈 Generate Recs
            </button>
          </div>
        </div>

        ${error ? `<div class="error">⚠️ ${error}</div>` : ''}

        <div class="content">
          ${loading && insights.length === 0 ? `
            <div class="loading">
              <div>⚡ Loading insights and recommendations...</div>
            </div>
          ` : `
            <div class="tabs">
              <button class="tab active" data-tab="insights">
                Insights
                <span class="tab-badge">${insights.length}</span>
              </button>
              <button class="tab" data-tab="recommendations">
                Recommendations
                <span class="tab-badge">${recommendations.length}</span>
              </button>
              <button class="tab" data-tab="changes">
                Changes
                <span class="tab-badge">${priceChanges.length}</span>
              </button>
            </div>

            <div id="tab-insights">
              ${insights.length === 0 ? `
                <div class="empty-state">
                  <h4>No insights yet</h4>
                  <p>Insights will appear as the system analyzes your parking data.</p>
                </div>
              ` : insights.map(insight => `
                <div class="item">
                  <div class="item-header">
                    <h4 class="item-title">${insight.kind || 'General'} Insight</h4>
                  </div>
                  <p class="item-text">${insight.narrative_text || 'No description available'}</p>
                  <div class="item-meta">
                    ${insight.confidence ? `Confidence: ${Math.round(insight.confidence * 100)}% • ` : ''}
                    ${new Date(insight.created_at).toLocaleString()}
                  </div>
                </div>
              `).join('')}
            </div>

            <div id="tab-recommendations" style="display: none;">
              ${recommendations.length === 0 ? `
                <div class="empty-state">
                  <h4>No recommendations</h4>
                  <p>Click "Generate Recs" to create AI-powered pricing recommendations.</p>
                </div>
              ` : recommendations.map(rec => `
                <div class="item">
                  <div class="item-header">
                    <h4 class="item-title">${rec.type || 'Price Adjustment'}</h4>
                    <span class="status status-${rec.status}">${rec.status}</span>
                  </div>
                  <p class="item-text">${rec.rationale_text || 'No rationale provided'}</p>
                  <div class="item-meta">
                    ${rec.confidence ? `Confidence: ${Math.round(rec.confidence * 100)}% • ` : ''}
                    ${new Date(rec.created_at).toLocaleString()}
                  </div>
                </div>
              `).join('')}
            </div>

            <div id="tab-changes" style="display: none;">
              ${priceChanges.length === 0 ? `
                <div class="empty-state">
                  <h4>No price changes</h4>
                  <p>Price changes will appear when recommendations are applied.</p>
                </div>
              ` : priceChanges.map(change => `
                <div class="item">
                  <div class="item-header">
                    <div class="price-change ${change.change_pct > 0 ? 'price-increase' : 'price-decrease'}">
                      $${(change.prev_price || 0).toFixed(2)} → $${change.new_price.toFixed(2)}
                      ${change.change_pct ? `(${change.change_pct > 0 ? '+' : ''}${(change.change_pct * 100).toFixed(1)}%)` : ''}
                    </div>
                    <span class="status status-${change.status}">${change.status}</span>
                  </div>
                  ${this.mode === 'execute' ? `
                    <div class="change-actions">
                      ${change.status === 'pending' ? `
                        <button class="btn btn-sm btn-success" data-action="apply" data-change-id="${change.id}">
                          ▶️ Apply
                        </button>
                      ` : ''}
                      ${change.status === 'applied' ? `
                        <button class="btn btn-sm btn-danger" data-action="revert" data-change-id="${change.id}">
                          ↩️ Revert
                        </button>
                      ` : ''}
                    </div>
                  ` : ''}
                  <div class="item-meta">
                    Zone: ${change.zone_id} • ${new Date(change.created_at).toLocaleString()}
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  attachEventListeners() {
    // Generate recommendations button
    const generateBtn = this.shadowRoot.getElementById('generate-btn');
    if (generateBtn) {
      generateBtn.onclick = () => this.generateRecommendations();
    }

    // Tab switching
    const tabs = this.shadowRoot.querySelectorAll('.tab');
    tabs.forEach(tab => {
      tab.onclick = () => {
        const targetTab = tab.dataset.tab;

        // Update active tab
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show/hide content
        const contents = this.shadowRoot.querySelectorAll('[id^="tab-"]');
        contents.forEach(content => {
          content.style.display = content.id === `tab-${targetTab}` ? 'block' : 'none';
        });
      };
    });

    // Change action buttons
    const actionButtons = this.shadowRoot.querySelectorAll('[data-action]');
    actionButtons.forEach(button => {
      button.onclick = () => {
        const action = button.dataset.action;
        const changeId = button.dataset.changeId;

        if (action === 'apply') {
          if (confirm('Are you sure you want to apply this price change?')) {
            this.applyChange(changeId);
          }
        } else if (action === 'revert') {
          if (confirm('Are you sure you want to revert this price change?')) {
            this.revertChange(changeId);
          }
        }
      };
    });
  }

  async revertChange(changeId) {
    if (!this.apiClient) return;

    try {
      const response = await this.apiClient.revertPriceChange(changeId);
      if (response.success) {
        this.loadData();

        this.dispatchEvent(new CustomEvent('revertRequest', {
          detail: { changeId, zoneId: this.zoneId },
          bubbles: true
        }));
      } else {
        this.data.error = response.error || 'Failed to revert change';
        this.render();
      }
    } catch (error) {
      this.data.error = 'Failed to revert change';
      this.render();
    }
  }
}

// Simple API client for the web component
class AnalystApiClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    try {
      const response = await fetch(url, { ...options, headers });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getInsights(zoneId) {
    const params = new URLSearchParams();
    if (zoneId) params.append('zone_id', zoneId);
    return this.request(`/insights?${params.toString()}`);
  }

  async getRecommendations(zoneId) {
    const params = new URLSearchParams();
    if (zoneId) params.append('zone_id', zoneId);
    return this.request(`/recommendations?${params.toString()}`);
  }

  async getPriceChanges(zoneId) {
    const params = new URLSearchParams();
    if (zoneId) params.append('zone_id', zoneId);
    return this.request(`/changes?${params.toString()}`);
  }

  async generateRecommendations(zoneId, context) {
    return this.request('/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify({
        zone_id: zoneId,
        context: context || undefined,
      }),
    });
  }

  async applyPriceChange(changeId, force = false) {
    return this.request('/changes/apply', {
      method: 'POST',
      body: JSON.stringify({
        change_id: changeId,
        force,
      }),
    });
  }

  async revertPriceChange(changeId, reason) {
    return this.request('/changes/revert', {
      method: 'POST',
      body: JSON.stringify({
        change_id: changeId,
        reason,
      }),
    });
  }
}

// Register the custom element
customElements.define('level-analyst-card', LevelAnalystCard);