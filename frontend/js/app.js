document.addEventListener("DOMContentLoaded", () => {
  // Navigation Tabs
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");

      if (btn.dataset.tab === "staff-tab") loadTriageQueue();
      if (btn.dataset.tab === "analytics-tab") loadDashboardAnalytics();
    });
  });

  // SUBMIT GRIEVANCE
  const grievanceForm = document.getElementById("grievance-form");
  const submissionResult = document.getElementById("submission-result");

  if (grievanceForm) {
    grievanceForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      submissionResult.className = "alert-box hidden";

      const payload = {
        citizen_name: document.getElementById("citizen_name").value,
        citizen_phone: document.getElementById("citizen_phone").value,
        category: document.getElementById("category").value,
        priority: document.getElementById("priority").value,
        ward: document.getElementById("ward").value,
        location: document.getElementById("location").value,
        description: document.getElementById("description").value,
        photo_url: document.getElementById("photo_url").value
      };

      try {
        const res = await fetch("/api/v1/complaints", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
          submissionResult.className = "alert-box alert-success";
          submissionResult.innerHTML = `
            <strong>Success! Your grievance has been registered.</strong><br>
            Tracking ID: <strong>${data.tracking_id}</strong><br>
            SLA Resolution Target: <strong>${new Date(data.sla_deadline).toLocaleString()}</strong><br>
            Please save your Tracking ID to monitor progress.
          `;
          grievanceForm.reset();
        } else {
          submissionResult.className = "alert-box alert-error";
          submissionResult.textContent = data.error || "Failed to submit grievance.";
        }
      } catch (err) {
        submissionResult.className = "alert-box alert-error";
        submissionResult.textContent = "Network error connecting to municipal server.";
      }
    });
  }

  // TRACK STATUS
  const trackBtn = document.getElementById("track-btn");
  const trackInput = document.getElementById("track-input");
  const trackingDetails = document.getElementById("tracking-details");

  async function fetchTracking(id) {
    if (!id) return;
    try {
      const res = await fetch(`/api/v1/complaints/${encodeURIComponent(id.trim())}`);
      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Grievance not found.");
        trackingDetails.classList.add("hidden");
        return;
      }

      trackingDetails.classList.remove("hidden");
      document.getElementById("ticket-id").textContent = data.tracking_id;
      document.getElementById("ticket-title").textContent = `${data.category} - ${data.location}`;
      document.getElementById("ticket-meta").textContent = `Reported by ${data.citizen_name} on ${new Date(data.created_at).toLocaleString()}`;
      
      const badge = document.getElementById("ticket-status-badge");
      badge.className = `badge badge-${data.status}`;
      badge.textContent = data.status;

      const slaBadge = document.getElementById("ticket-sla-badge");
      slaBadge.className = `sla-badge sla-${data.sla_analysis.status_label}`;
      slaBadge.textContent = `SLA: ${data.sla_analysis.status_label} (${data.sla_analysis.hours_remaining}h)`;

      document.getElementById("ticket-desc").textContent = data.description;
      document.getElementById("ticket-loc").textContent = data.location;
      document.getElementById("ticket-ward").textContent = data.ward;
      document.getElementById("ticket-eng").textContent = data.assigned_engineer || "Unassigned (Awaiting Triage)";
      document.getElementById("ticket-deadline").textContent = new Date(data.sla_deadline).toLocaleString();

      // Timeline
      const timelineBox = document.getElementById("ticket-timeline");
      timelineBox.innerHTML = "";
      (data.timeline || []).forEach(item => {
        const el = document.createElement("div");
        el.className = "timeline-item";
        el.innerHTML = `
          <strong>${item.action}</strong> by <em>${item.performed_by}</em><br>
          <small>${item.notes || ""}</small><br>
          <span class="timeline-time">${new Date(item.timestamp).toLocaleString()}</span>
        `;
        timelineBox.appendChild(el);
      });

      // Feedback section
      const fbSec = document.getElementById("feedback-section");
      if (data.status === "RESOLVED") {
        fbSec.classList.remove("hidden");
        setupFeedbackListeners(data.tracking_id);
      } else {
        fbSec.classList.add("hidden");
      }

    } catch (err) {
      alert("Error retrieving grievance record.");
    }
  }

  if (trackBtn) {
    trackBtn.addEventListener("click", () => fetchTracking(trackInput.value));
  }

  function setupFeedbackListeners(trackingId) {
    const acceptBtn = document.getElementById("accept-resolution-btn");
    const reopenBtn = document.getElementById("reopen-complaint-btn");

    acceptBtn.onclick = async () => {
      const rating = document.getElementById("rating-val").value;
      const comments = document.getElementById("feedback-comment").value;
      await submitFeedbackReq(trackingId, rating, comments, false);
    };

    reopenBtn.onclick = async () => {
      const rating = document.getElementById("rating-val").value;
      const comments = document.getElementById("feedback-comment").value;
      await submitFeedbackReq(trackingId, rating, comments, true);
    };
  }

  async function submitFeedbackReq(trackingId, rating, comments, reopen) {
    const res = await fetch(`/api/v1/complaints/${trackingId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, comments, reopen })
    });
    if (res.ok) {
      alert(reopen ? "Grievance has been reopened for reinspection." : "Thank you! Grievance is now closed.");
      fetchTracking(trackingId);
    }
  }

  // STAFF QUEUE
  async function loadTriageQueue() {
    const tbody = document.getElementById("triage-table-body");
    const statusVal = document.getElementById("filter-status").value;
    const wardVal = document.getElementById("filter-ward").value;

    let url = "/api/v1/complaints?";
    if (statusVal) url += `status=${encodeURIComponent(statusVal)}&`;
    if (wardVal) url += `ward=${encodeURIComponent(wardVal)}&`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      tbody.innerHTML = "";

      if (!data.complaints || data.complaints.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center">No grievances match criteria.</td></tr>`;
        return;
      }

      data.complaints.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${item.tracking_id}</strong></td>
          <td>${item.category}</td>
          <td>${item.ward}</td>
          <td><span class="badge badge-${item.priority}">${item.priority}</span></td>
          <td><span class="sla-badge sla-${item.sla_analysis.status_label}">${item.sla_analysis.status_label}</span></td>
          <td><span class="badge badge-${item.status}">${item.status}</span></td>
          <td>${item.assigned_engineer || "<em>None</em>"}</td>
          <td>
            <button class="btn btn-secondary action-btn" data-id="${item.tracking_id}" data-action="assign">Assign</button>
            <button class="btn btn-secondary action-btn" data-id="${item.tracking_id}" data-action="status">Status</button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      document.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", () => openActionModal(btn.dataset.id, btn.dataset.action));
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Failed to load queue.</td></tr>`;
    }
  }

  document.getElementById("filter-status")?.addEventListener("change", loadTriageQueue);
  document.getElementById("filter-ward")?.addEventListener("change", loadTriageQueue);
  document.getElementById("refresh-queue-btn")?.addEventListener("click", loadTriageQueue);

  // MODAL ACTIONS
  const modal = document.getElementById("action-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  document.getElementById("modal-close")?.addEventListener("click", () => modal.classList.add("hidden"));

  function openActionModal(trackingId, actionType) {
    modal.classList.remove("hidden");
    if (actionType === "assign") {
      modalTitle.textContent = `Assign Engineer - ${trackingId}`;
      modalBody.innerHTML = `
        <div class="form-group">
          <label>Select Field Engineer</label>
          <select id="modal-engineer-select">
            <option value="Er. Ramesh Kumar (Roads & Infra)">Er. Ramesh Kumar (Roads & Infra)</option>
            <option value="Er. Priya Sundaram (Sanitation & Waste)">Er. Priya Sundaram (Sanitation & Waste)</option>
            <option value="Er. Anthony Das (Drainage & Water)">Er. Anthony Das (Drainage & Water)</option>
            <option value="Er. K. Suresh (Electrical / Streetlights)">Er. K. Suresh (Electrical / Streetlights)</option>
          </select>
        </div>
        <button class="btn btn-primary" id="modal-submit-assign">Confirm Assignment</button>
      `;
      document.getElementById("modal-submit-assign").onclick = async () => {
        const eng = document.getElementById("modal-engineer-select").value;
        const res = await fetch(`/api/v1/complaints/${trackingId}/assign`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ assigned_engineer: eng })
        });
        if (res.ok) {
          modal.classList.add("hidden");
          loadTriageQueue();
        }
      };
    } else if (actionType === "status") {
      modalTitle.textContent = `Update Lifecycle Status - ${trackingId}`;
      modalBody.innerHTML = `
        <div class="form-group">
          <label>New Status</label>
          <select id="modal-status-select">
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>
        <div class="form-group">
          <label>Engineer / Inspection Remarks</label>
          <textarea id="modal-notes" rows="2" placeholder="Details of work carried out..."></textarea>
        </div>
        <div class="form-group">
          <label>Resolution Proof Photo URL</label>
          <input type="url" id="modal-proof" placeholder="https://example.com/repaired_pothole.jpg">
        </div>
        <button class="btn btn-primary" id="modal-submit-status">Apply Status Update</button>
      `;
      document.getElementById("modal-submit-status").onclick = async () => {
        const st = document.getElementById("modal-status-select").value;
        const notes = document.getElementById("modal-notes").value;
        const proof = document.getElementById("modal-proof").value;
        const res = await fetch(`/api/v1/complaints/${trackingId}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: st, notes, resolution_proof: proof, performed_by: "Field Engineer" })
        });
        if (res.ok) {
          modal.classList.add("hidden");
          loadTriageQueue();
        }
      };
    }
  }

  // DASHBOARD ANALYTICS
  async function loadDashboardAnalytics() {
    try {
      const res = await fetch("/api/v1/dashboard/stats");
      const data = await res.json();

      document.getElementById("stat-total").textContent = data.total_complaints;
      const pending = (data.by_status.SUBMITTED || 0) + (data.by_status.ASSIGNED || 0) + (data.by_status.IN_PROGRESS || 0) + (data.by_status.REOPENED || 0);
      const resolved = (data.by_status.RESOLVED || 0) + (data.by_status.CLOSED || 0);

      document.getElementById("stat-pending").textContent = pending;
      document.getElementById("stat-resolved").textContent = resolved;
      document.getElementById("stat-rating").textContent = `${data.average_citizen_rating} / 5 (${data.total_feedback_count} reviews)`;

      const breakdown = document.getElementById("breakdown-container");
      breakdown.innerHTML = `
        <div>
          <h4>By Civic Category</h4>
          <ul>
            ${Object.entries(data.by_category).map(([k, v]) => `<li><strong>${k}:</strong> ${v}</li>`).join("") || "<li>No data</li>"}
          </ul>
        </div>
        <div>
          <h4>By Ward Distribution</h4>
          <ul>
            ${Object.entries(data.by_ward).map(([k, v]) => `<li><strong>${k}:</strong> ${v}</li>`).join("") || "<li>No data</li>"}
          </ul>
        </div>
      `;
    } catch (err) {
      console.error(err);
    }
  }
});
