/**
 * Notes Manager — Client-Side Interactivity & API Integration
 * Implements CSRF handling, Native <dialog closedby="any"> fallback,
 * Toast notifications, Notes/Tasks CRUD, PDF Quiz Runner, and SMTP/Socket/FTP controls.
 */

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.getAttribute('content');
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

function showToast(message, isError = false) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast';
  if (isError) {
    toast.style.backgroundColor = '#853737';
    toast.style.borderLeftColor = '#FAF5F4';
  }
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3800);
}

async function apiRequest(url, method = 'GET', body = null, isFormData = false) {
  const headers = {
    'X-CSRFToken': getCsrfToken(),
  };
  if (!isFormData && body !== null) {
    headers['Content-Type'] = 'application/json';
  }
  const options = {
    method,
    headers,
    credentials: 'same-origin',
  };
  if (body !== null) {
    options.body = isFormData ? body : JSON.stringify(body);
  }
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.status === 'error') {
    throw new Error(data.message || `Request failed (${response.status})`);
  }
  return data;
}

// Mandatory fallback for browsers without native <dialog closedby="any"> support
function initDialogLightDismiss() {
  const dialogs = document.querySelectorAll('dialog.app-modal');
  dialogs.forEach((dialog) => {
    if (!('closedBy' in HTMLDialogElement.prototype)) {
      dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const isDialogContent =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (isDialogContent) return;
        dialog.close();
      });
    }
  });
}

function openModal(dialogId) {
  const dialog = document.getElementById(dialogId);
  if (dialog && typeof dialog.showModal === 'function') {
    dialog.showModal();
  }
}

function closeModal(dialogId) {
  const dialog = document.getElementById(dialogId);
  if (dialog && typeof dialog.close === 'function') {
    dialog.close();
  }
}

// Toggle covered/uncovered status for a note
async function toggleNoteCovered(noteId, covered, reloadAfter = true) {
  try {
    const res = await apiRequest(`/api/notes/${noteId}/`, 'PATCH', { covered });
    showToast(covered ? 'Note marked as Covered! Progress updated.' : 'Note marked as Not Covered.');
    if (reloadAfter) {
      setTimeout(() => window.location.reload(), 650);
    }
    return res;
  } catch (err) {
    showToast(err.message, true);
  }
}

async function deleteNoteById(noteId) {
  if (!confirm('Are you sure you want to delete this study note?')) return;
  try {
    await apiRequest(`/api/notes/${noteId}/`, 'DELETE');
    showToast('Note deleted.');
    setTimeout(() => window.location.reload(), 500);
  } catch (err) {
    showToast(err.message, true);
  }
}

// Toggle task completion
async function toggleTaskCompleted(taskId, completed) {
  try {
    const res = await apiRequest(`/api/tasks/${taskId}/`, 'PATCH', { completed });
    showToast(res.summary_text || 'Task updated!');
    setTimeout(() => window.location.reload(), 500);
  } catch (err) {
    showToast(err.message, true);
  }
}

async function deleteTaskById(taskId) {
  if (!confirm('Delete this task?')) return;
  try {
    await apiRequest(`/api/tasks/${taskId}/`, 'DELETE');
    showToast('Task deleted.');
    setTimeout(() => window.location.reload(), 450);
  } catch (err) {
    showToast(err.message, true);
  }
}

async function deleteResourceById(resourceId) {
  if (!confirm('Delete this resource file?')) return;
  try {
    await apiRequest(`/api/resources/${resourceId}/`, 'DELETE');
    showToast('Resource deleted.');
    setTimeout(() => window.location.reload(), 450);
  } catch (err) {
    showToast(err.message, true);
  }
}

// Send SMTP Progress Report
async function submitProgressReportEmail(event) {
  event.preventDefault();
  const form = event.target;
  const emailInput = form.querySelector('input[name="email"]');
  const statusBox = document.getElementById('smtp-report-output');
  const submitBtn = form.querySelector('button[type="submit"]');
  if (!emailInput || !emailInput.value.trim()) {
    showToast('Please enter a valid email address.', true);
    return;
  }
  try {
    if (submitBtn) submitBtn.disabled = true;
    const res = await apiRequest('/api/email/report/', 'POST', {
      email: emailInput.value.trim(),
    });
    showToast(res.message || 'Progress report sent!');
    if (statusBox) {
      statusBox.style.display = 'block';
      statusBox.textContent = res.report_preview || res.message;
    }
  } catch (err) {
    showToast(err.message, true);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

// Ping TCP Socket Server
async function pingSocketService() {
  try {
    const res = await apiRequest('/api/socket/status/', 'POST', {
      message: 'STUDY_HEARTBEAT_PING',
    });
    const sock = res.socket || {};
    showToast(`Socket ${sock.socket_service} (${sock.latency_ms} ms) — Pings: ${sock.session_pings}`);
    const out = document.getElementById('socket-live-json');
    if (out) {
      out.textContent = JSON.stringify(sock, null, 2);
    }
  } catch (err) {
    showToast(err.message, true);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initDialogLightDismiss();
  const sidebarToggle = document.getElementById('sidebar-toggle-btn');
  const sidebar = document.getElementById('app-sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }
});
