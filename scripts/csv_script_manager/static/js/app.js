// CSV Editor Application JavaScript

class CSVEditor {
    constructor() {
        this.currentFilename = null;
        this.csvData = [];
        this.headers = null; // Store column headers if detected
        this.selectedRow = null;
        this.isDirty = false;
        this.currentScriptToRun = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadFileList();
        this.loadLastFile();
        this.loadScriptsList();
        this.loadApiKeysStatus();
    }
    
    loadLastFile() {
        // Load the last opened/saved file on page refresh
        fetch('/api/last-file')
            .then(response => response.json())
            .then(data => {
                if (data.filename) {
                    this.loadFile(data.filename);
                }
            })
            .catch(error => {
                console.error('Error loading last file:', error);
            });
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });
        
        // API Keys form submission
        document.getElementById('apiKeysForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveApiKeys();
        });
        
        
        // CSV Editor buttons
        document.getElementById('newFileBtn').addEventListener('click', () => this.newFile());
        document.getElementById('loadFileBtn').addEventListener('click', () => this.showLoadModal());
        document.getElementById('saveBtn').addEventListener('click', () => this.saveFile());
        document.getElementById('saveAsBtn').addEventListener('click', () => this.showSaveAsModal());
        document.getElementById('exportBtn').addEventListener('click', () => this.exportFile());
        
        // Script actions buttons
        document.getElementById('newScriptBtn').addEventListener('click', () => this.newScript());
        document.getElementById('uploadScriptBtn').addEventListener('click', () => {
            document.getElementById('uploadScriptFileInput').click();
        });
        document.getElementById('uploadScriptFileInput').addEventListener('change', (e) => this.handleUploadScriptFile(e));
        document.getElementById('downloadScriptUrlBtn').addEventListener('click', () => this.showDownloadScriptUrlModal());
        
        // Toolbar buttons
        document.getElementById('addRowBtn').addEventListener('click', () => this.addRow());
        document.getElementById('addColBtn').addEventListener('click', () => this.addColumn());
        document.getElementById('deleteRowBtn').addEventListener('click', () => this.deleteRow());
        
        // File input
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileSelect(e));
        document.getElementById('fileSelectInput').addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Modal close buttons
        document.getElementById('closeLoadModal').addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideLoadModal();
        });
        document.getElementById('closeSaveAsModal').addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideSaveAsModal();
        });
        document.getElementById('cancelSaveAsBtn').addEventListener('click', () => this.hideSaveAsModal());
        document.getElementById('confirmSaveAsBtn').addEventListener('click', () => this.confirmSaveAs());
        document.getElementById('closeRunScriptModal').addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideRunScriptModal();
        });
        document.getElementById('cancelRunScriptBtn').addEventListener('click', () => this.hideRunScriptModal());
        document.getElementById('confirmRunScriptBtn').addEventListener('click', () => this.runScript());
        document.getElementById('saveOutputBtn').addEventListener('click', () => this.saveScriptOutput());
        document.getElementById('closeAddScriptModal').addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideAddScriptModal();
        });
        document.getElementById('cancelAddScriptBtn').addEventListener('click', () => this.hideAddScriptModal());
        document.getElementById('confirmAddScriptBtn').addEventListener('click', () => this.createScript());
        document.getElementById('confirmDownloadScriptUrlBtn').addEventListener('click', () => this.downloadScriptFromUrl());
        document.getElementById('cancelDownloadScriptUrlBtn').addEventListener('click', () => this.hideDownloadScriptUrlModal());
        document.getElementById('closeDownloadScriptUrlModal').addEventListener('click', () => this.hideDownloadScriptUrlModal());
        
        // Click outside modal to close
        document.getElementById('loadModal').addEventListener('click', (e) => {
            if (e.target.id === 'loadModal') {
                this.hideLoadModal();
            }
        });
        
        document.getElementById('saveAsModal').addEventListener('click', (e) => {
            if (e.target.id === 'saveAsModal') {
                this.hideSaveAsModal();
            }
        });
        
        document.getElementById('runScriptModal').addEventListener('click', (e) => {
            if (e.target.id === 'runScriptModal') {
                this.hideRunScriptModal();
            }
        });
        
        document.getElementById('addScriptModal').addEventListener('click', (e) => {
            if (e.target.id === 'addScriptModal') {
                this.hideAddScriptModal();
            }
        });
        
        // File upload area click - only trigger on the upload area itself
        const uploadArea = document.getElementById('fileUploadArea');
        const fileSelectInput = document.getElementById('fileSelectInput');
        
        uploadArea.addEventListener('click', (e) => {
            // Only trigger file input if clicking directly on upload area, not on child elements
            if (e.target === uploadArea || e.target.closest('p') || e.target.closest('svg')) {
                fileSelectInput.click();
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#2563eb';
            uploadArea.style.background = '#f8fafc';
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#e2e8f0';
            uploadArea.style.background = 'transparent';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#e2e8f0';
            uploadArea.style.background = 'transparent';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].name.endsWith('.csv')) {
                this.loadFileFromFileObject(files[0]);
            }
        });
        
        // Table cell editing
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('editable-cell')) {
                e.target.focus();
            }
        });
        
        // Track changes
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('editable-cell')) {
                this.isDirty = true;
                this.updateSaveButtons();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 's') {
                    e.preventDefault();
                    if (this.currentFilename) {
                        this.saveFile();
                    } else {
                        this.showSaveAsModal();
                    }
                }
            }
        });
    }
    
    newFile() {
        if (this.isDirty && !confirm('You have unsaved changes. Create a new file anyway?')) {
            return;
        }
        
        this.currentFilename = null;
        this.csvData = [['']];
        this.headers = null;
        this.isDirty = false;
        this.renderTable();
        this.updateUI();
        this.showNotification('New file created', 'success');
    }
    
    showLoadModal() {
        document.getElementById('loadModal').classList.add('active');
        this.loadFileList();
    }
    
    hideLoadModal() {
        document.getElementById('loadModal').classList.remove('active');
    }
    
    showSaveAsModal() {
        document.getElementById('saveAsFilename').value = this.currentFilename || 'untitled.csv';
        document.getElementById('saveAsModal').classList.add('active');
        document.getElementById('saveAsFilename').focus();
        document.getElementById('saveAsFilename').select();
    }
    
    hideSaveAsModal() {
        document.getElementById('saveAsModal').classList.remove('active');
    }
    
    confirmSaveAs() {
        const filename = document.getElementById('saveAsFilename').value.trim();
        if (!filename) {
            this.showNotification('Please enter a filename', 'error');
            return;
        }
        
        const finalFilename = filename.endsWith('.csv') ? filename : filename + '.csv';
        this.currentFilename = finalFilename;
        this.saveFile();
        this.hideSaveAsModal();
    }
    
    loadFileList() {
        fetch('/api/list')
            .then(response => response.json())
            .then(data => {
                const fileList = document.getElementById('fileList');
                if (data.files && data.files.length > 0) {
                    fileList.innerHTML = data.files.map(file => `
                        <div class="file-item" data-filename="${file.name}">
                            <div>
                                <div class="file-item-name">${this.escapeHtml(file.name)}</div>
                                <div class="file-item-size">${this.formatFileSize(file.size)}</div>
                            </div>
                        </div>
                    `).join('');
                    
                    // Add click handlers
                    fileList.querySelectorAll('.file-item').forEach(item => {
                        item.addEventListener('click', (e) => {
                            e.stopPropagation(); // Prevent event bubbling
                            const filename = item.dataset.filename;
                            this.loadFile(filename);
                        });
                    });
                } else {
                    fileList.innerHTML = '<div class="file-item loading">No saved files</div>';
                }
            })
            .catch(error => {
                console.error('Error loading file list:', error);
                document.getElementById('fileList').innerHTML = '<div class="file-item loading">Error loading files</div>';
            });
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file && file.name.endsWith('.csv')) {
            this.loadFileFromFileObject(file);
        } else {
            this.showNotification('Please select a CSV file', 'error');
        }
    }
    
    loadFileFromFileObject(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const content = e.target.result;
                const result = this.parseCSV(content);
                this.csvData = result.data;
                this.headers = result.headers;
                this.currentFilename = file.name;
                this.isDirty = false;
                this.renderTable();
                this.updateUI();
                this.hideLoadModal();
                // Automatically save the loaded file locally
                this.autoSaveLoadedFile(file.name, content);
            } catch (error) {
                this.showNotification('Error parsing CSV file: ' + error.message, 'error');
            }
        };
        reader.readAsText(file);
    }
    
    autoSaveLoadedFile(filename, content) {
        // Ensure .csv extension
        const finalFilename = filename.endsWith('.csv') ? filename : filename + '.csv';
        
        // Convert content to rows format for saving
        const rows = this.parseCSV(content);
        const rowsToSave = rows.headers ? [rows.headers, ...rows.data] : rows.data;
        
        fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: finalFilename,
                rows: rowsToSave
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // Don't show error for auto-save, just log it
                console.error('Auto-save failed:', data.error);
                return;
            }
            // Update current filename to the saved one
            this.currentFilename = finalFilename;
            this.updateUI();
            this.loadFileList();
        })
        .catch(error => {
            // Don't show error for auto-save, just log it
            console.error('Auto-save error:', error);
        });
    }
    
    loadFile(filename) {
        fetch(`/api/load?filename=${encodeURIComponent(filename)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    this.showNotification(data.error, 'error');
                    return;
                }
                
                // Parse the loaded data to detect headers
                const result = this.parseCSV(data.content || this.rowsToCSV(data.rows));
                this.csvData = result.data;
                this.headers = result.headers;
                this.currentFilename = data.filename;
                this.isDirty = false;
                this.renderTable();
                this.updateUI();
                this.hideLoadModal();
                // File is already saved locally (it's from the saved files list)
                this.showNotification('File loaded successfully', 'success');
            })
            .catch(error => {
                this.showNotification('Error loading file: ' + error.message, 'error');
            });
    }
    
    saveFile() {
        if (!this.currentFilename) {
            this.showSaveAsModal();
            return Promise.reject('No filename');
        }
        
        const rows = this.getTableData();
        // Include headers as first row if they exist
        const rowsToSave = this.headers ? [this.headers, ...rows] : rows;
        
        return fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: this.currentFilename,
                rows: rowsToSave
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                this.showNotification(data.error, 'error');
                return Promise.reject(data.error);
            }
            
            this.isDirty = false;
            this.updateSaveButtons();
            this.showNotification('File saved successfully', 'success');
            this.loadFileList();
            return Promise.resolve();
        })
        .catch(error => {
            this.showNotification('Error saving file: ' + error.message, 'error');
            return Promise.reject(error);
        });
    }
    
    exportFile() {
        if (!this.currentFilename) {
            this.showNotification('No file to export', 'error');
            return;
        }
        
        // Use the existing download endpoint
        const url = `/api/download?filename=${encodeURIComponent(this.currentFilename)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = this.currentFilename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.showNotification('File exported successfully', 'success');
    }
    
    addRow() {
        const numCols = this.csvData[0] ? this.csvData[0].length : 1;
        const newRow = new Array(numCols).fill('');
        this.csvData.push(newRow);
        this.renderTable();
        this.isDirty = true;
        this.updateSaveButtons();
        this.saveToLocalStorage();
    }
    
    addColumn() {
        const numCols = this.csvData[0] ? this.csvData[0].length : 0;
        const colName = this.headers ? `Column ${numCols + 1}` : `Column ${numCols + 1}`;
        
        // Add to headers if they exist
        if (this.headers) {
            this.headers.push(colName);
        }
        
        // Add to all data rows
        this.csvData.forEach(row => {
            row.push('');
        });
        this.renderTable();
        this.isDirty = true;
        this.updateSaveButtons();
        this.saveToLocalStorage();
    }
    
    deleteRow() {
        if (this.selectedRow === null) {
            this.showNotification('Please select a row to delete', 'error');
            return;
        }
        
        this.csvData.splice(this.selectedRow, 1);
        this.selectedRow = null;
        this.renderTable();
        this.isDirty = true;
        this.updateSaveButtons();
        this.saveToLocalStorage();
    }
    
    renderTable() {
        const tableHead = document.getElementById('tableHead');
        const tableBody = document.getElementById('tableBody');
        const emptyState = document.getElementById('emptyState');
        const tableWrapper = document.getElementById('tableWrapper');
        
        if (this.csvData.length === 0) {
            tableWrapper.style.display = 'none';
            emptyState.classList.remove('hidden');
            return;
        }
        
        tableWrapper.style.display = 'block';
        emptyState.classList.add('hidden');
        
        // Render header - use detected headers or default column names
        const numCols = this.csvData[0] ? this.csvData[0].length : 1;
        let headerHTML = '<tr><th class="row-header">#</th>';
        for (let i = 0; i < numCols; i++) {
            const headerName = this.headers && this.headers[i] !== undefined 
                ? this.escapeHtml(String(this.headers[i])) 
                : `Column ${i + 1}`;
            headerHTML += `<th class="col-header" contenteditable="true">${headerName}</th>`;
        }
        headerHTML += '</tr>';
        tableHead.innerHTML = headerHTML;
        
        // Update headers when user edits header cells
        tableHead.querySelectorAll('.col-header').forEach((header, index) => {
            header.addEventListener('blur', () => {
                if (!this.headers) {
                    this.headers = new Array(numCols).fill('');
                }
                this.headers[index] = header.textContent;
                this.isDirty = true;
                this.updateSaveButtons();
            });
        });
        
        // Render body
        let bodyHTML = '';
        this.csvData.forEach((row, rowIndex) => {
            bodyHTML += `<tr data-row-index="${rowIndex}">`;
            bodyHTML += `<td class="row-header">${rowIndex + 1}</td>`;
            for (let i = 0; i < numCols; i++) {
                const cellValue = row[i] !== undefined ? this.escapeHtml(String(row[i])) : '';
                bodyHTML += `<td class="editable-cell" contenteditable="true">${cellValue}</td>`;
            }
            bodyHTML += '</tr>';
        });
        tableBody.innerHTML = bodyHTML;
        
        // Add row click handlers
        tableBody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                if (!e.target.classList.contains('editable-cell')) {
                    tableBody.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
                    row.classList.add('selected');
                    this.selectedRow = parseInt(row.dataset.rowIndex);
                    document.getElementById('deleteRowBtn').disabled = false;
                }
            });
        });
        
        // Update cell values on edit
        tableBody.querySelectorAll('.editable-cell').forEach((cell, index) => {
            const rowIndex = Math.floor(index / numCols);
            const colIndex = index % numCols;
            
            cell.addEventListener('blur', () => {
                if (!this.csvData[rowIndex]) {
                    this.csvData[rowIndex] = new Array(numCols).fill('');
                }
                this.csvData[rowIndex][colIndex] = cell.textContent;
            });
        });
    }
    
    getTableData() {
        const rows = [];
        const tableBody = document.getElementById('tableBody');
        const rows_elements = tableBody.querySelectorAll('tr');
        
        rows_elements.forEach(row => {
            const cells = row.querySelectorAll('.editable-cell');
            const rowData = [];
            cells.forEach(cell => {
                rowData.push(cell.textContent);
            });
            rows.push(rowData);
        });
        
        return rows;
    }
    
    updateUI() {
        const fileInfoBar = document.getElementById('fileInfoBar');
        const fileName = document.getElementById('fileName');
        const fileStats = document.getElementById('fileStats');
        
        if (this.currentFilename) {
            fileInfoBar.style.display = 'flex';
            fileName.textContent = this.currentFilename;
            const numRows = this.csvData.length;
            const numCols = this.csvData[0] ? this.csvData[0].length : 0;
            fileStats.textContent = `${numRows} rows × ${numCols} columns`;
        } else {
            fileInfoBar.style.display = 'none';
        }
        
        const hasData = this.csvData.length > 0;
        document.getElementById('addRowBtn').disabled = !hasData;
        document.getElementById('addColBtn').disabled = !hasData;
        document.getElementById('deleteRowBtn').disabled = true;
        
        this.updateSaveButtons();
    }
    
    rowsToCSV(rows) {
        // Helper to convert rows back to CSV string for parsing
        return rows.map(row => {
            return row.map(field => {
                const fieldStr = String(field || '');
                if (fieldStr.includes(',') || fieldStr.includes('"') || fieldStr.includes('\n')) {
                    return '"' + fieldStr.replace(/"/g, '""') + '"';
                }
                return fieldStr;
            }).join(',');
        }).join('\n');
    }
    
    updateSaveButtons() {
        const hasData = this.csvData && this.csvData.length > 0 && this.csvData[0] && this.csvData[0].length > 0;
        const canSave = hasData && (this.currentFilename || this.isDirty);
        const saveBtn = document.getElementById('saveBtn');
        const saveAsBtn = document.getElementById('saveAsBtn');
        const exportBtn = document.getElementById('exportBtn');
        saveBtn.disabled = !canSave || !this.isDirty;
        saveAsBtn.disabled = !hasData;
        exportBtn.disabled = !this.currentFilename || !hasData;
    }
    
    parseCSV(content) {
        const rows = [];
        const lines = content.split('\n');
        
        for (let line of lines) {
            line = line.trim();
            if (line) {
                rows.push(this.parseCSVLine(line));
            }
        }
        
        if (rows.length === 0) {
            return { data: [['']], headers: null };
        }
        
        // Normalize row lengths
        const maxCols = Math.max(...rows.map(row => row.length));
        rows.forEach(row => {
            while (row.length < maxCols) {
                row.push('');
            }
        });
        
        // Detect if first row is headers
        // Heuristic: if first row contains mostly non-numeric text, treat as headers
        const firstRow = rows[0];
        const isHeaderRow = this.detectHeaders(firstRow, rows.length > 1 ? rows[1] : null);
        
        if (isHeaderRow && rows.length > 1) {
            // First row is headers, rest is data
            return {
                headers: firstRow,
                data: rows.slice(1)
            };
        } else {
            // No headers detected, all rows are data
            return {
                headers: null,
                data: rows
            };
        }
    }
    
    detectHeaders(firstRow, secondRow) {
        // If we only have one row, it's probably data, not headers
        if (!secondRow) {
            return false;
        }
        
        // Count how many fields in first row look like headers (non-numeric, text-like)
        let headerLikeCount = 0;
        let totalFields = 0;
        
        for (let i = 0; i < firstRow.length; i++) {
            const firstValue = String(firstRow[i] || '').trim();
            const secondValue = secondRow[i] !== undefined ? String(secondRow[i] || '').trim() : '';
            
            if (firstValue) {
                totalFields++;
                
                // Check if first row value looks like a header:
                // - Contains letters (not just numbers)
                // - Doesn't look like a number
                // - Is different from the corresponding value in second row (if exists)
                const isNumeric = /^-?\d*\.?\d+$/.test(firstValue);
                const hasLetters = /[a-zA-Z]/.test(firstValue);
                const isDifferent = secondValue && firstValue.toLowerCase() !== secondValue.toLowerCase();
                
                if ((hasLetters && !isNumeric) || isDifferent) {
                    headerLikeCount++;
                }
            }
        }
        
        // If more than 50% of fields look like headers, treat first row as headers
        return totalFields > 0 && (headerLikeCount / totalFields) > 0.5;
    }
    
    parseCSVLine(line) {
        const fields = [];
        let currentField = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            
            if (char === '"') {
                if (inQuotes && line[i + 1] === '"') {
                    currentField += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                fields.push(currentField);
                currentField = '';
            } else {
                currentField += char;
            }
        }
        
        fields.push(currentField);
        return fields;
    }
    
    showNotification(message, type = 'success') {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    
    hideRunScriptModal() {
        document.getElementById('runScriptModal').classList.remove('active');
        this.currentScriptToRun = null;
    }
    
    saveScriptOutput() {
        const outputContent = document.getElementById('outputContent').textContent;
        const outputError = document.getElementById('outputError').textContent;
        const outputStatus = document.getElementById('outputStatus').textContent;
        const scriptName = document.getElementById('runScriptName').textContent;
        
        if (!outputContent && !outputError) {
            this.showNotification('No output to save', 'error');
            return;
        }
        
        // Combine all output
        let fullOutput = outputStatus + '\n\n';
        if (outputContent) {
            fullOutput += outputContent;
        }
        if (outputError) {
            fullOutput += '\n\nErrors:\n' + outputError;
        }
        
        // Create a blob and download it
        const blob = new Blob([fullOutput], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const filename = scriptName ? `${scriptName.replace('.py', '')}_output_${timestamp}.txt` : `script_output_${timestamp}.txt`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        this.showNotification('Output saved successfully', 'success');
    }
    
    runScript() {
        const scriptName = this.currentScriptToRun;
        
        if (!scriptName) {
            this.showNotification('No script selected', 'error');
            return;
        }
        
        if (!this.currentFilename) {
            this.showNotification('No CSV file loaded', 'error');
            return;
        }
        
        const runBtn = document.getElementById('confirmRunScriptBtn');
        const outputDiv = document.getElementById('scriptOutput');
        const outputStatus = document.getElementById('outputStatus');
        const outputContent = document.getElementById('outputContent');
        const outputError = document.getElementById('outputError');
        
        // Show output area
        outputDiv.style.display = 'block';
        outputStatus.className = 'output-status running';
        outputStatus.textContent = 'Running script...';
        outputContent.textContent = '';
        outputError.style.display = 'none';
        outputError.textContent = '';
        runBtn.disabled = true;
        
        fetch('/api/run-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                script: scriptName,
                csv_file: this.currentFilename
            })
        })
        .then(response => response.json())
        .then(data => {
            runBtn.disabled = false;
            
            if (data.error) {
                outputStatus.className = 'output-status error';
                outputStatus.textContent = 'Error';
                outputError.textContent = data.error;
                outputError.style.display = 'block';
                return;
            }
            
            if (data.success) {
                outputStatus.className = 'output-status success';
                outputStatus.textContent = `Script completed successfully (exit code: ${data.exit_code})`;
            } else {
                outputStatus.className = 'output-status error';
                outputStatus.textContent = `Script failed (exit code: ${data.exit_code})`;
            }
            
            // Combine stdout and stderr for display
            let combinedOutput = '';
            if (data.stdout) {
                combinedOutput += data.stdout;
            }
            if (data.stderr) {
                // For successful scripts, stderr is informational, not an error
                if (data.success) {
                    // Append stderr to stdout for successful scripts
                    if (combinedOutput && !combinedOutput.endsWith('\n')) {
                        combinedOutput += '\n';
                    }
                    combinedOutput += data.stderr;
                } else {
                    // For failed scripts, show stderr as error
                    outputError.textContent = data.stderr;
                    outputError.style.display = 'block';
                }
            }
            
            if (combinedOutput) {
                outputContent.textContent = combinedOutput;
            } else {
                outputContent.textContent = '(No output)';
            }
            
            this.showNotification(
                data.success ? 'Script executed successfully' : 'Script execution failed',
                data.success ? 'success' : 'error'
            );
        })
        .catch(error => {
            runBtn.disabled = false;
            outputStatus.className = 'output-status error';
            outputStatus.textContent = 'Error';
            outputError.textContent = 'Error executing script: ' + error.message;
            outputError.style.display = 'block';
            this.showNotification('Error executing script: ' + error.message, 'error');
        });
    }
    
    
    hideAddScriptModal() {
        document.getElementById('addScriptModal').classList.remove('active');
    }
    
    getDefaultScriptTemplate() {
        return `#!/usr/bin/env python3
"""
Python script to process CSV files.
The CSV file path is passed as the first command-line argument.
"""

import sys
import os

def main():
    # Get CSV file path from command line argument
    if len(sys.argv) < 2:
        print("Error: No CSV file provided")
        print("Usage: python3 script.py <csv_file_path>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Your script logic here
    print(f"Processing CSV file: {csv_file}")
    print("Script execution completed successfully!")

if __name__ == '__main__':
    main()`;
    }
    
    hideAddScriptModal() {
        document.getElementById('addScriptModal').classList.remove('active');
    }
    
    createScript() {
        const scriptName = document.getElementById('scriptName').value.trim();
        const scriptContent = document.getElementById('scriptContent').value.trim();
        
        if (!scriptName) {
            this.showNotification('Please enter a script name', 'error');
            return;
        }
        
        if (!scriptContent) {
            this.showNotification('Please enter script content', 'error');
            return;
        }
        
        fetch('/api/create-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                script_name: scriptName,
                script_content: scriptContent
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                this.showNotification(data.error, 'error');
                return;
            }
            
            this.hideAddScriptModal();
            this.showNotification('Script saved successfully', 'success');
            // Reload scripts list if on scripts tab
            if (document.getElementById('scriptsTab').classList.contains('active')) {
                this.loadScriptsList();
            }
        })
        .catch(error => {
            this.showNotification('Error creating script: ' + error.message, 'error');
        });
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            if (content.id === tabName + 'Tab') {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
        
        // Update body background color
        document.body.className = '';
        if (tabName) {
            document.body.classList.add('tab-' + tabName);
        }
        
        // Load scripts list when switching to scripts tab
        if (tabName === 'scripts') {
            this.loadScriptsList();
        }
        
        // Load API keys status when switching to API keys tab
        if (tabName === 'apikeys') {
            this.loadApiKeysStatus();
        }
    }
    
    loadScriptsList() {
        const scriptsList = document.getElementById('scriptsList');
        scriptsList.innerHTML = '<div class="loading-message">Loading scripts...</div>';
        
        fetch('/api/scripts')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    scriptsList.innerHTML = '<div class="loading-message">Error loading scripts</div>';
                    return;
                }
                
                if (!data.scripts || data.scripts.length === 0) {
                    scriptsList.innerHTML = '<div class="loading-message">No scripts available. Create one to get started!</div>';
                    return;
                }
                
                scriptsList.innerHTML = '';
                data.scripts.forEach(script => {
                    const scriptItem = document.createElement('div');
                    scriptItem.className = 'script-item';
                    const hasDescription = script.description && script.description.trim();
                    const descriptionHtml = hasDescription 
                        ? `<div class="script-item-description">${this.escapeHtml(script.description)}</div>`
                        : '';
                    scriptItem.innerHTML = `
                        <div class="script-item-content">
                            <span class="script-item-name">${this.escapeHtml(script.name)}</span>
                            ${descriptionHtml}
                        </div>
                        <div class="script-item-actions">
                            <button class="btn btn-sm btn-script-run" data-script="${this.escapeHtml(script.name)}" data-action="run" title="Run Script">
                                <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                </svg> Run
                            </button>
                            <button class="btn btn-sm btn-secondary" data-script="${this.escapeHtml(script.name)}" data-action="edit" title="Edit Script">
                                <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                </svg> Edit
                            </button>
                            <button class="btn btn-sm btn-danger" data-script="${this.escapeHtml(script.name)}" data-action="delete" title="Delete Script">
                                <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg> Delete
                            </button>
                        </div>
                    `;
                    
                    // Make script item clickable to expand/collapse if it has a description
                    if (hasDescription) {
                        scriptItem.classList.add('script-item-expandable');
                        scriptItem.addEventListener('click', (e) => {
                            // Don't expand if clicking on action buttons
                            if (e.target.closest('.script-item-actions')) {
                                return;
                            }
                            scriptItem.classList.toggle('expanded');
                        });
                    }
                    
                    scriptsList.appendChild(scriptItem);
                });
                
                // Add event listeners to action buttons
                scriptsList.querySelectorAll('[data-action]').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const scriptName = e.target.closest('[data-script]').dataset.script;
                        const action = e.target.closest('[data-action]').dataset.action;
                        this.handleScriptAction(scriptName, action);
                    });
                });
            })
            .catch(error => {
                console.error('Error loading scripts:', error);
                scriptsList.innerHTML = '<div class="loading-message">Error loading scripts</div>';
            });
    }
    
    handleScriptAction(scriptName, action) {
        if (action === 'run') {
            this.runScriptFromList(scriptName);
        } else if (action === 'edit') {
            this.editScriptFromList(scriptName);
        } else if (action === 'delete') {
            this.deleteScript(scriptName);
        }
    }
    
    runScriptFromList(scriptName) {
        if (!this.currentFilename) {
            this.showNotification('Please load a CSV file first', 'error');
            this.switchTab('csv');
            return;
        }
        
        // Check if there are unsaved changes
        if (this.isDirty) {
            if (confirm('You have unsaved changes. Save before running the script?')) {
                const savePromise = this.saveFile();
                if (savePromise && typeof savePromise.then === 'function') {
                    savePromise.then(() => {
                        this.executeScript(scriptName);
                    }).catch(() => {
                        this.executeScript(scriptName);
                    });
                } else {
                    setTimeout(() => {
                        this.executeScript(scriptName);
                    }, 500);
                }
                return;
            }
        }
        
        this.executeScript(scriptName);
    }
    
    executeScript(scriptName) {
        document.getElementById('runScriptName').textContent = scriptName;
        document.getElementById('scriptCsvFile').textContent = this.currentFilename;
        document.getElementById('runScriptModal').classList.add('active');
        document.getElementById('scriptOutput').style.display = 'none';
        
        // Store script name for execution
        this.currentScriptToRun = scriptName;
    }
    
    editScriptFromList(scriptName) {
        fetch(`/api/load-script?script=${encodeURIComponent(scriptName)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    this.showNotification(data.error, 'error');
                    return;
                }
                
                document.getElementById('addScriptModalTitle').textContent = 'Edit Script';
                document.getElementById('scriptName').value = data.filename || scriptName;
                document.getElementById('scriptContent').value = data.content || '';
                document.getElementById('addScriptModal').classList.add('active');
            })
            .catch(error => {
                this.showNotification('Error loading script: ' + error.message, 'error');
            });
    }
    
    deleteScript(scriptName) {
        if (!confirm(`Are you sure you want to delete "${scriptName}"?`)) {
            return;
        }
        
        fetch('/api/delete-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ script_name: scriptName })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                this.showNotification(data.error, 'error');
                return;
            }
            
            this.showNotification('Script deleted successfully', 'success');
            this.loadScriptsList();
        })
        .catch(error => {
            this.showNotification('Error deleting script: ' + error.message, 'error');
        });
    }
    
    newScript() {
        document.getElementById('addScriptModalTitle').textContent = 'New Script';
        document.getElementById('scriptName').value = '';
        document.getElementById('scriptContent').value = '';
        document.getElementById('addScriptModal').classList.add('active');
        document.getElementById('scriptName').focus();
    }
    
    handleUploadScriptFile(event) {
        const file = event.target.files[0];
        if (file && file.name.endsWith('.py')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const content = e.target.result;
                    document.getElementById('addScriptModalTitle').textContent = 'Upload Script';
                    document.getElementById('scriptName').value = file.name;
                    document.getElementById('scriptContent').value = content;
                    document.getElementById('addScriptModal').classList.add('active');
                } catch (error) {
                    this.showNotification('Error reading script file: ' + error.message, 'error');
                }
            };
            reader.readAsText(file);
        } else {
            this.showNotification('Please select a Python (.py) file', 'error');
        }
        event.target.value = '';
    }
    
    showDownloadScriptUrlModal() {
        document.getElementById('downloadScriptUrlModal').classList.add('active');
        document.getElementById('scriptUrlInput').value = '';
        document.getElementById('scriptUrlInput').focus();
    }
    
    hideDownloadScriptUrlModal() {
        document.getElementById('downloadScriptUrlModal').classList.remove('active');
    }
    
    downloadScriptFromUrl() {
        const url = document.getElementById('scriptUrlInput').value.trim();
        if (!url) {
            this.showNotification('Please enter a URL', 'error');
            return;
        }
        
        try {
            new URL(url);
        } catch (e) {
            this.showNotification('Invalid URL format', 'error');
            return;
        }
        
        const downloadBtn = document.getElementById('confirmDownloadScriptUrlBtn');
        downloadBtn.disabled = true;
        downloadBtn.textContent = 'Downloading...';
        
        fetch('/api/download-script-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        })
        .then(response => response.json())
        .then(data => {
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Download';
            
            if (data.error) {
                this.showNotification(data.error, 'error');
                return;
            }
            
            this.hideDownloadScriptUrlModal();
            
            // Handle multiple scripts from folder download
            if (data.multiple && data.scripts && data.scripts.length > 0) {
                // Save all scripts automatically
                let savedCount = 0;
                let failedCount = 0;
                
                data.scripts.forEach((script, index) => {
                    fetch('/api/create-script', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            script_name: script.filename,
                            script_content: script.content
                        })
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.error) {
                            failedCount++;
                            console.error(`Error saving ${script.filename}:`, result.error);
                        } else {
                            savedCount++;
                        }
                        
                        // When all scripts are processed, show notification and reload list
                        if (savedCount + failedCount === data.scripts.length) {
                            if (failedCount === 0) {
                                this.showNotification(`Successfully downloaded and saved ${savedCount} script(s)`, 'success');
                            } else {
                                this.showNotification(`Saved ${savedCount} script(s), ${failedCount} failed`, 'error');
                            }
                            this.loadScriptsList();
                        }
                    })
                    .catch(error => {
                        failedCount++;
                        console.error(`Error saving ${script.filename}:`, error);
                        if (savedCount + failedCount === data.scripts.length) {
                            this.showNotification(`Saved ${savedCount} script(s), ${failedCount} failed`, 'error');
                            this.loadScriptsList();
                        }
                    });
                });
            } else {
                // Single script - open in editor
                document.getElementById('addScriptModalTitle').textContent = 'Downloaded Script';
                document.getElementById('scriptName').value = data.filename || 'downloaded_script.py';
                document.getElementById('scriptContent').value = data.content || '';
                document.getElementById('addScriptModal').classList.add('active');
                this.showNotification('Script downloaded successfully. Please save it to add to your scripts list.', 'success');
            }
        })
        .catch(error => {
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Download';
            this.showNotification('Error downloading script: ' + error.message, 'error');
        });
    }
    
    loadApiKeysStatus() {
        // Load environment name
        fetch('/api/environment-info')
            .then(response => response.json())
            .then(data => {
                if (data.environment) {
                    document.getElementById('environmentName').textContent = data.environment;
                } else {
                    document.getElementById('environmentName').textContent = 'Unknown';
                }
            })
            .catch(error => {
                console.error('Error loading environment info:', error);
                document.getElementById('environmentName').textContent = 'Error';
            });
        
        // Security: Load API keys status (check if they're set, but never receive actual values)
        // The backend only returns boolean values indicating presence
        fetch('/api/api-keys-status')
            .then(response => response.json())
            .then(data => {
                const envVars = [
                    { name: 'X_CP_API_ID', statusId: 'status_x_cp_api_id', inputId: 'x_cp_api_id' },
                    { name: 'X_CP_API_KEY', statusId: 'status_x_cp_api_key', inputId: 'x_cp_api_key' },
                    { name: 'X_ECM_API_ID', statusId: 'status_x_ecm_api_id', inputId: 'x_ecm_api_id' },
                    { name: 'X_ECM_API_KEY', statusId: 'status_x_ecm_api_key', inputId: 'x_ecm_api_key' },
                    { name: 'TOKEN', statusId: 'status_token', inputId: 'ncm_api_token' }
                ];
                
                envVars.forEach(({ name, statusId, inputId }) => {
                    const statusEl = document.getElementById(statusId);
                    const inputEl = document.getElementById(inputId);
                    if (statusEl) {
                        // Security: Only boolean values are received, never actual key values
                        const isSet = data[name] === true;
                        statusEl.className = 'status-indicator ' + (isSet ? 'set' : 'not-set');
                        // Add text label after the indicator
                        statusEl.setAttribute('data-label', isSet ? 'LOADED' : 'NOT FOUND');
                        
                        // Clear input field - user can enter values to validate
                        // The checkmark/X indicator shows if a key is set, but we don't show the value
                        if (inputEl) {
                            inputEl.value = '';
                            inputEl.removeAttribute('data-populated');
                        }
                    }
                });
            })
            .catch(error => {
                // Security: Don't log any key-related information
                console.error('Error loading API keys status:', error);
            });
    }
    
    saveApiKeys() {
        const form = document.getElementById('apiKeysForm');
        const formData = new FormData(form);
        const apiKeys = {};
        
        // Security: Only include fields that have values
        // Only send actual values entered by user
        for (const [key, value] of formData.entries()) {
            if (value && value.trim()) {
                apiKeys[key] = value.trim();
            }
        }
        
        if (Object.keys(apiKeys).length === 0) {
            this.showNotification('Please enter at least one API key', 'error');
            return;
        }
        
        const saveBtn = form.querySelector('button[type="submit"]');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
        
        // Security: Values are sent over HTTPS in the request body
        // The response will never contain the actual values
        fetch('/api/set-api-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(apiKeys)
        })
        .then(response => response.json())
        .then(data => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save API Keys';
            
            if (data.error) {
                this.showNotification(data.error, 'error');
                return;
            }
            
            this.showNotification('API keys saved successfully', 'success');
            // Security: Clear form immediately after successful save
            // Reload status to update indicators and show dots for newly saved keys
            form.reset();
            this.loadApiKeysStatus();
        })
        .catch(error => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save API Keys';
            this.showNotification('Error saving API keys: ' + error.message, 'error');
        });
    }
    
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const editor = new CSVEditor();
    // Set initial background color based on active tab
    const activeTab = document.querySelector('.tab-btn.active');
    if (activeTab) {
        const tabName = activeTab.dataset.tab;
        if (tabName) {
            document.body.classList.add('tab-' + tabName);
        }
    }
});

