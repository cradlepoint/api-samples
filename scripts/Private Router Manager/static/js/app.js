/**
 * Private Router Manager - Vanilla JavaScript
 * CSV editor and deployment UI
 */

(function () {
  'use strict';

  const state = {
    headers: [],
    rows: [],
    deployType: 'licenses',
  };

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => el.querySelectorAll(sel);

  const csvUpload = $('#csvUpload');
  const csvTable = $('#csvTable');
  const csvHead = $('#csvHead');
  const csvBody = $('#csvBody');
  const csvTableWrap = $('#csvTableWrap');
  const emptyState = $('#emptyState');
  const btnDownload = $('#btnDownload');
  const btnNewCsv = $('#btnNewCsv');
  const btnSave = $('#btnSave');
  const btnSaveAs = $('#btnSaveAs');
  const btnAddRow = $('#btnAddRow');
  const btnAddCol = $('#btnAddCol');
  const drawer = $('#drawer');
  const drawerToggle = $('#drawerToggle');
  const drawerArrow = $('#drawerArrow');
  const drawerContent = $('#drawerContent');
  const deployType = $('#deployType');
  const deployFile = $('#deployFile');
  const btnUploadDeploy = $('#btnUploadDeploy');
  const availableFiles = $('#availableFiles');
  const btnDeploy = $('#btnDeploy');
  const deployStatus = $('#deployStatus');
  const saveAsModal = $('#saveAsModal');
  const saveAsFilename = $('#saveAsFilename');
  const btnSaveAsCancel = $('#btnSaveAsCancel');
  const btnSaveAsConfirm = $('#btnSaveAsConfirm');
  const btnOpen = $('#btnOpen');
  const openModal = $('#openModal');
  const openFileList = $('#openFileList');
  const btnOpenCancel = $('#btnOpenCancel');
  const btnOpenConfirm = $('#btnOpenConfirm');
  const helpBtn = $('#helpBtn');
  const helpModal = $('#helpModal');
  const helpContent = $('#helpContent');
  const helpClose = $('#helpClose');
  const sameCredentials = $('#sameCredentials');
  const credFields = $('#credFields');
  const samePort = $('#samePort');
  const portField = $('#portField');
  const globalUsername = $('#globalUsername');
  const globalPassword = $('#globalPassword');
  const globalPort = $('#globalPort');

  function hasIpColumn(headers) {
    return headers.some(h => {
      const n = String(h).trim().toLowerCase().replace(/\s/g, '_');
      return n === 'ip_address' || n === 'ipaddress' || n.includes('ip_address') || n.includes('ipaddress');
    });
  }

  function renderTable() {
    if (state.headers.length === 0) {
      state.headers = ['ip_address'];
      state.rows = [['']];
    }
    csvTableWrap.style.display = 'block';
    emptyState.classList.remove('visible');
    csvHead.innerHTML = '';
    csvBody.innerHTML = '';

    const headerRow = document.createElement('tr');
    state.headers.forEach((h, i) => {
      const th = document.createElement('th');
      const span = document.createElement('span');
      span.textContent = h;
      th.appendChild(span);
      const delBtn = document.createElement('button');
      delBtn.className = 'btn-icon';
      delBtn.textContent = '×';
      delBtn.title = 'Delete column';
      delBtn.onclick = (e) => { e.stopPropagation(); deleteColumn(i); };
      th.appendChild(delBtn);
      headerRow.appendChild(th);
    });
    const thActions = document.createElement('th');
    thActions.className = 'col-actions';
    headerRow.appendChild(thActions);
    csvHead.appendChild(headerRow);

    state.rows.forEach((row, rowIdx) => {
      const tr = document.createElement('tr');
      state.headers.forEach((_, colIdx) => {
        const td = document.createElement('td');
        const input = document.createElement('input');
        input.type = 'text';
        input.value = row[colIdx] ?? '';
        input.dataset.row = rowIdx;
        input.dataset.col = colIdx;
        input.onchange = () => {
          state.rows[rowIdx][colIdx] = input.value;
        };
        td.appendChild(input);
        tr.appendChild(td);
      });
      const tdActions = document.createElement('td');
      tdActions.className = 'row-actions';
      const delBtn = document.createElement('button');
      delBtn.className = 'btn-icon';
      delBtn.textContent = '×';
      delBtn.title = 'Delete row';
      delBtn.onclick = () => deleteRow(rowIdx);
      tdActions.appendChild(delBtn);
      tr.appendChild(tdActions);
      csvBody.appendChild(tr);
    });
  }

  function collectFromTable() {
    const rows = [];
    $$('#csvBody tr').forEach(tr => {
      const row = [];
      const inputs = tr.querySelectorAll('td:not(.row-actions) input');
      inputs.forEach(input => row.push(input.value));
      rows.push(row);
    });
    return rows;
  }

  function deleteRow(idx) {
    state.rows.splice(idx, 1);
    renderTable();
  }

  function deleteColumn(idx) {
    if (state.headers.length <= 1) return;
    state.headers.splice(idx, 1);
    state.rows.forEach(row => row.splice(idx, 1));
    renderTable();
  }

  function addRow() {
    if (state.headers.length === 0) {
      state.headers = ['ip_address'];
    }
    state.rows.push(new Array(state.headers.length).fill(''));
    renderTable();
  }

  function addColumn() {
    const name = prompt('Column name:', 'column' + (state.headers.length + 1));
    if (!name) return;
    state.headers.push(name.trim() || 'column');
    state.rows.forEach(row => row.push(''));
    renderTable();
  }

  function csvToBlob() {
    const lines = [state.headers.join(',')];
    const data = state.headers.length ? collectFromTable() : state.rows;
    data.forEach(row => {
      lines.push(row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
    });
    return new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  }

  function downloadCsv() {
    if (state.headers.length === 0) {
      showDeployStatus('No data to download.', true);
      return;
    }
    const blob = csvToBlob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'routers.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function saveCsv() {
    if (state.headers.length === 0) {
      showDeployStatus('No data to save.', true);
      return;
    }
    if (!hasIpColumn(state.headers)) {
      showDeployStatus('CSV must have "ip address" or "ip_address" column.', true);
      return;
    }
    const data = { headers: state.headers, rows: collectFromTable() };
    fetch('/api/csv/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, filename: 'routers.csv' }),
    })
      .then(r => r.json())
      .then(body => {
        if (body.error) showDeployStatus(body.error, true);
        else {
          saveLastFile('routers.csv');
          showDeployStatus('Saved to ' + body.saved, false);
        }
      })
      .catch(e => showDeployStatus('Save failed: ' + e.message, true));
  }

  function saveAsCsv() {
    if (state.headers.length === 0) {
      showDeployStatus('No data to save.', true);
      return;
    }
    saveAsFilename.value = 'routers.csv';
    saveAsModal.classList.add('visible');
  }

  function doSaveAs() {
    let filename = saveAsFilename.value.trim();
    if (!filename) return;
    if (!filename.toLowerCase().endsWith('.csv')) filename += '.csv';
    if (!hasIpColumn(state.headers)) {
      showDeployStatus('CSV must have "ip address" or "ip_address" column.', true);
      return;
    }
    const data = { headers: state.headers, rows: collectFromTable(), filename };
    fetch('/api/csv/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
      .then(r => r.json())
      .then(body => {
        saveAsModal.classList.remove('visible');
        if (body.error) showDeployStatus(body.error, true);
        else {
          saveLastFile(filename);
          showDeployStatus('Saved to ' + body.saved, false);
        }
      })
      .catch(e => {
        saveAsModal.classList.remove('visible');
        showDeployStatus('Save failed: ' + e.message, true);
      });
  }

  function uploadCsv(ev) {
    const file = ev.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    fetch('/api/csv/upload', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(body => {
        if (body.error) {
          showDeployStatus(body.error, true);
          return;
        }
        state.headers = body.headers;
        state.rows = body.rows;
        renderTable();
        showDeployStatus('CSV loaded: ' + state.rows.length + ' routers', false);
      })
      .catch(e => showDeployStatus('Upload failed: ' + e.message, true));
    ev.target.value = '';
  }

  // Drawer
  function updateDrawerArrow() {
    if (drawerArrow) drawerArrow.textContent = drawer.classList.contains('expanded') ? '\u25B6' : '\u25C0';
  }
  drawerToggle.addEventListener('click', () => {
    drawer.classList.toggle('expanded');
    updateDrawerArrow();
  });
  drawer.classList.add('expanded');
  updateDrawerArrow();

  // Theme toggle
  const themeToggle = $('#themeToggle');
  function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {
      document.body.classList.add('light-mode');
      if (themeToggle) themeToggle.textContent = '🌙';
    } else {
      document.body.classList.remove('light-mode');
      if (themeToggle) themeToggle.textContent = '☀';
    }
  }
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('light-mode');
      const isLight = document.body.classList.contains('light-mode');
      localStorage.setItem('theme', isLight ? 'light' : 'dark');
      themeToggle.textContent = isLight ? '🌙' : '☀';
    });
  }
  initTheme();

  const sshPortField = $('#sshPortField');
  const sshPortInput = $('#sshPort');

  const ncosDownloadSection = $('#ncosDownloadSection');
  const ncosDownloadToggle = $('#ncosDownloadToggle');
  const ncosDownloadContent = $('#ncosDownloadContent');
  const ncosApiStatus = $('#ncosApiStatus');
  const ncosCpId = $('#ncosCpId');
  const ncosCpKey = $('#ncosCpKey');
  const ncosEcmId = $('#ncosEcmId');
  const ncosEcmKey = $('#ncosEcmKey');
  const btnSaveNcosKeys = $('#btnSaveNcosKeys');
  const ncosVersion = $('#ncosVersion');
  const ncosModel = $('#ncosModel');
  const btnNcosSearch = $('#btnNcosSearch');
  const ncosFirmwareList = $('#ncosFirmwareList');
  const btnNcosDownload = $('#btnNcosDownload');

  if (ncosDownloadToggle) {
    ncosDownloadToggle.addEventListener('click', () => {
      ncosDownloadSection.classList.toggle('expanded');
      ncosDownloadToggle.setAttribute('aria-expanded', ncosDownloadSection.classList.contains('expanded'));
    });
  }

  const fileUploadSection = $('#fileUploadSection');
  const availableFilesSection = $('#availableFilesSection');
  const btnOnlineStatus = $('#btnOnlineStatus');

  deployType.addEventListener('change', () => {
    state.deployType = deployType.value;
    const isOnlineStatus = state.deployType === 'online_status';
    fileUploadSection.style.display = isOnlineStatus ? 'none' : 'block';
    availableFilesSection.style.display = isOnlineStatus ? 'none' : 'block';
    if (btnDeploy) btnDeploy.style.display = isOnlineStatus ? 'none' : 'block';
    if (btnOnlineStatus) btnOnlineStatus.style.display = isOnlineStatus ? 'block' : 'none';
    sshPortField.style.display = state.deployType === 'sdk_apps' ? 'block' : 'none';
    ncosDownloadSection.style.display = state.deployType === 'ncos' ? 'block' : 'none';
    if (state.deployType === 'ncos') {
      loadNcosConfig();
      ncosDownloadSection.classList.remove('expanded');
    }
    if (!isOnlineStatus) loadAvailableFiles();
  });

  function loadNcosConfig() {
    fetch('/api/ncos/config')
      .then(r => r.json())
      .then(cfg => {
        if (ncosApiStatus) {
          if (cfg.configured && cfg.source === 'env') {
            ncosApiStatus.textContent = 'API keys loaded from environment';
            ncosApiStatus.className = 'ncos-api-status ncos-status-ok';
            ncosCpId.value = ncosCpKey.value = ncosEcmId.value = ncosEcmKey.value = '';
          } else if (cfg.configured) {
            ncosApiStatus.textContent = '';
            ncosApiStatus.className = 'ncos-api-status';
            ncosCpId.value = cfg['X-CP-API-ID'] || '';
            ncosCpKey.value = cfg['X-CP-API-KEY'] || '';
            ncosEcmId.value = cfg['X-ECM-API-ID'] || '';
            ncosEcmKey.value = cfg['X-ECM-API-KEY'] || '';
          } else {
            ncosApiStatus.textContent = '';
            ncosApiStatus.className = 'ncos-api-status';
          }
        }
      })
      .catch(() => {});
  }

  if (btnSaveNcosKeys) {
    btnSaveNcosKeys.addEventListener('click', () => {
      fetch('/api/ncos/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          'X-CP-API-ID': ncosCpId.value,
          'X-CP-API-KEY': ncosCpKey.value,
          'X-ECM-API-ID': ncosEcmId.value,
          'X-ECM-API-KEY': ncosEcmKey.value,
        }),
      })
        .then(r => r.json())
        .then(() => showDeployStatus('API keys saved.', false))
        .catch(e => showDeployStatus('Save failed: ' + e.message, true));
    });
  }

  if (btnNcosSearch) {
    btnNcosSearch.addEventListener('click', () => {
      const version = ncosVersion.value.trim();
      const model = ncosModel.value.trim();
      if (!version || !model) {
        showDeployStatus('Enter version and model.', true);
        return;
      }
      showDeployStatus('Searching...', false);
      fetch('/api/ncos/firmwares?version=' + encodeURIComponent(version) + '&model=' + encodeURIComponent(model))
        .then(r => r.json())
        .then(body => {
          if (body.error) {
            showDeployStatus(body.error, true);
            return;
          }
          ncosFirmwareList.innerHTML = '';
          (body.firmwares || []).forEach((f, i) => {
            const opt = document.createElement('option');
            opt.value = f.url;
            opt.textContent = (f.url || '').replace(/\//g, '');
            opt.dataset.url = f.url;
            ncosFirmwareList.appendChild(opt);
          });
          showDeployStatus((body.firmwares || []).length + ' NCOS file(s) found.', false);
        })
        .catch(e => showDeployStatus('Search failed: ' + e.message, true));
    });
  }

  if (btnNcosDownload) {
    btnNcosDownload.addEventListener('click', () => {
      const version = ncosVersion.value.trim();
      const model = ncosModel.value.trim();
      const opt = ncosFirmwareList.selectedOptions[0];
      const url = opt ? opt.value : '';
      if (!version || !model || !url) {
        showDeployStatus('Search first and select an NCOS.', true);
        return;
      }
      showDeployStatus('Downloading...', false);
      fetch('/api/ncos/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version, model, url }),
      })
        .then(r => r.json())
        .then(body => {
          if (body.error) showDeployStatus(body.error, true);
          else {
            loadAvailableFiles();
            showDeployStatus('Downloaded: ' + body.name, false);
          }
        })
        .catch(e => showDeployStatus('Download failed: ' + e.message, true));
    });
  }

  function loadAvailableFiles() {
    if (state.deployType === 'online_status') return;
    fetch('/api/files/' + state.deployType)
      .then(r => r.json())
      .then(body => {
        availableFiles.innerHTML = '';
        (body.files || []).forEach(f => {
          const opt = document.createElement('option');
          opt.value = f.path;
          opt.textContent = f.name;
          availableFiles.appendChild(opt);
        });
      })
      .catch(() => {});
  }

  if (btnOnlineStatus) {
    btnOnlineStatus.addEventListener('click', () => {
      const headers = state.headers;
      const rows = state.headers.length ? collectFromTable() : state.rows;
      if (!headers.length || !rows.length) {
        showDeployStatus('Load router CSV first.', true);
        return;
      }
      if (sameCredentials.checked && (!globalUsername.value || !globalPassword.value)) {
        showDeployStatus('Enter username and password when using same credentials.', true);
        return;
      }
      showDeployStatus('Checking...', false);
      fetch('/api/csv/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headers, rows }),
      })
        .then(() =>
          fetch('/api/online-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              same_credentials: sameCredentials.checked,
              username: globalUsername.value,
              password: globalPassword.value,
              same_port: samePort.checked,
              port: parseInt(globalPort.value, 10) || 8080,
            }),
          })
        )
        .then(r => r.json())
        .then(body => {
          if (body.error) showDeployStatus(body.error, true);
          else {
            state.headers = body.headers;
            state.rows = body.rows;
            renderTable();
            showDeployStatus('Online status added to CSV.', false);
          }
        })
        .catch(e => showDeployStatus('Check failed: ' + e.message, true));
    });
  }

  btnUploadDeploy.addEventListener('click', () => deployFile.click());

  deployFile.addEventListener('change', ev => {
    const file = ev.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    fetch('/api/files/' + state.deployType + '/upload', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(body => {
        if (body.error) showDeployStatus(body.error, true);
        else {
          loadAvailableFiles();
          showDeployStatus('Uploaded: ' + body.name, false);
        }
      })
      .catch(e => showDeployStatus('Upload failed: ' + e.message, true));
    ev.target.value = '';
  });

  function showDeployStatus(msg, isError) {
    deployStatus.textContent = msg;
    deployStatus.className = 'deploy-status' + (isError ? ' error' : ' success');
  }

  btnDeploy.addEventListener('click', () => {
    const path = availableFiles.value;
    if (!path) {
      showDeployStatus('Select a file to deploy.', true);
      return;
    }
    const data = {
      file_path: path,
      deploy_type: state.deployType,
      same_credentials: sameCredentials.checked,
      username: globalUsername.value,
      password: globalPassword.value,
      same_port: samePort.checked,
      port: parseInt(globalPort.value, 10) || 8080,
      ssh_port: parseInt(sshPortInput.value, 10) || 22,
    };
    if (data.same_credentials && (!data.username || !data.password)) {
      showDeployStatus('Enter username and password when using same credentials.', true);
      return;
    }
    const headers = state.headers;
    const rows = state.headers.length ? collectFromTable() : state.rows;
    if (!headers.length || !rows.length) {
      showDeployStatus('Load router CSV first.', true);
      return;
    }
    fetch('/api/csv/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headers, rows }),
    })
      .then(() =>
        fetch('/api/deploy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        })
      )
      .then(r => r.json())
      .then(body => {
        if (body.error) showDeployStatus(body.error, true);
        else showDeployStatus('Deployment complete. Log: ' + body.log, false);
      })
      .catch(e => showDeployStatus('Deploy failed: ' + e.message, true));
  });

  // Options visibility
  sameCredentials.addEventListener('change', () => {
    credFields.style.display = sameCredentials.checked ? 'flex' : 'none';
  });
  samePort.addEventListener('change', () => {
    portField.style.display = samePort.checked ? 'flex' : 'none';
  });
  credFields.style.display = sameCredentials.checked ? 'flex' : 'none';
  portField.style.display = samePort.checked ? 'flex' : 'none';

  // Load and save credentials
  function loadCredentials() {
    fetch('/api/config/credentials')
      .then(r => r.json())
      .then(cfg => {
        globalUsername.value = cfg.username || '';
        globalPassword.value = cfg.password || '';
        globalPort.value = String(cfg.port || 8080);
        if (cfg.last_file) {
          fetch('/api/csv/open?filename=' + encodeURIComponent(cfg.last_file))
            .then(r => r.json())
            .then(body => {
              if (!body.error && body.headers && body.rows) {
                state.headers = body.headers;
                state.rows = body.rows;
                renderTable();
              }
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
  }

  function saveLastFile(filename) {
    fetch('/api/config/credentials')
      .then(r => r.json())
      .then(cfg => {
        cfg.last_file = filename || '';
        return fetch('/api/config/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cfg),
        });
      })
      .catch(() => {});
  }

  let saveCredsTimer;
  function saveCredentials() {
    clearTimeout(saveCredsTimer);
    saveCredsTimer = setTimeout(() => {
      fetch('/api/config/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: globalUsername.value,
          password: globalPassword.value,
          port: parseInt(globalPort.value, 10) || 8080,
        }),
      }).catch(() => {});
    }, 500);
  }

  loadCredentials();
  if (globalUsername) globalUsername.addEventListener('input', saveCredentials);
  if (globalPassword) globalPassword.addEventListener('input', saveCredentials);
  if (globalPort) globalPort.addEventListener('input', saveCredentials);

  // Bind buttons
  function newCsv() {
    state.headers = [];
    state.rows = [];
    renderTable();
    showDeployStatus('New CSV started. Add rows or upload a file.', false);
  }

  if (btnOpen) {
    btnOpen.addEventListener('click', () => {
      fetch('/api/csv/list')
        .then(r => r.json())
        .then(body => {
          const files = body.files || [];
          openFileList.innerHTML = '';
          files.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.name;
            opt.textContent = f.name;
            openFileList.appendChild(opt);
          });
          fetch('/api/config/credentials')
            .then(r => r.json())
            .then(cfg => {
              const last = cfg.last_file || '';
              const idx = files.findIndex(f => f.name === last);
              openFileList.selectedIndex = idx >= 0 ? idx : 0;
            })
            .catch(() => { if (openFileList.options.length) openFileList.selectedIndex = 0; });
          openModal.classList.add('visible');
        })
        .catch(() => openModal.classList.add('visible'));
    });
  }

  if (btnOpenConfirm) {
    btnOpenConfirm.addEventListener('click', () => {
      const filename = openFileList.value;
      if (!filename) return;
      fetch('/api/csv/open?filename=' + encodeURIComponent(filename))
        .then(r => r.json())
        .then(body => {
          openModal.classList.remove('visible');
          if (body.error) {
            showDeployStatus(body.error, true);
            return;
          }
          state.headers = body.headers;
          state.rows = body.rows;
          renderTable();
          saveLastFile(filename);
          showDeployStatus('Opened: ' + filename, false);
        })
        .catch(e => {
          openModal.classList.remove('visible');
          showDeployStatus('Open failed: ' + e.message, true);
        });
    });
  }

  if (btnOpenCancel) {
    btnOpenCancel.addEventListener('click', () => openModal.classList.remove('visible'));
  }

  csvUpload.addEventListener('change', uploadCsv);
  btnDownload.addEventListener('click', downloadCsv);
  btnNewCsv.addEventListener('click', newCsv);
  btnSave.addEventListener('click', saveCsv);
  btnSaveAs.addEventListener('click', saveAsCsv);
  btnAddRow.addEventListener('click', addRow);
  btnAddCol.addEventListener('click', addColumn);

  btnSaveAsCancel.addEventListener('click', () => saveAsModal.classList.remove('visible'));
  btnSaveAsConfirm.addEventListener('click', doSaveAs);

  if (helpBtn && helpModal && helpContent) {
    helpBtn.addEventListener('click', () => {
      fetch('/api/readme')
        .then(r => r.ok ? r.text() : Promise.reject(new Error('Not found')))
        .then(md => {
          let html;
          if (typeof marked !== 'undefined') {
            html = (marked.parse || marked)(md);
          } else {
            html = md.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
          }
          helpContent.innerHTML = html;
          helpModal.classList.add('visible');
        })
        .catch(() => {
          helpContent.textContent = 'Help content not available.';
          helpModal.classList.add('visible');
        });
    });
  }
  if (helpClose) helpClose.addEventListener('click', () => helpModal.classList.remove('visible'));
  if (helpModal) helpModal.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.classList.remove('visible'); });

  (function initDeployUI() {
    state.deployType = deployType.value;
    const isOnlineStatus = state.deployType === 'online_status';
    if (fileUploadSection) fileUploadSection.style.display = isOnlineStatus ? 'none' : 'block';
    if (availableFilesSection) availableFilesSection.style.display = isOnlineStatus ? 'none' : 'block';
    if (btnDeploy) btnDeploy.style.display = isOnlineStatus ? 'none' : 'block';
    if (btnOnlineStatus) btnOnlineStatus.style.display = isOnlineStatus ? 'block' : 'none';
  })();
  loadAvailableFiles();
  renderTable();
  sshPortField.style.display = state.deployType === 'sdk_apps' ? 'block' : 'none';
  if (ncosDownloadSection) ncosDownloadSection.style.display = state.deployType === 'ncos' ? 'block' : 'none';
})();
