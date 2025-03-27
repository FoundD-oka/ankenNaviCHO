// 更新確認ボタンのアラートを削除するスクリプト
document.addEventListener('DOMContentLoaded', function() {
    // トースト表示関数がグローバルに定義されていない場合は定義する
    if (typeof window.showToast !== 'function') {
        window.showToast = function(message, type) {
            console.log(`Toast (${type}): ${message}`);
            
            const toast = document.createElement('div');
            toast.className = `toast-notification toast-${type}`;
            toast.innerHTML = `
                <div class="toast-content">
                    <div class="toast-message">${message}</div>
                </div>
            `;
            document.body.appendChild(toast);
            
            // アニメーション用に表示を遅らせる
            setTimeout(() => {
                toast.classList.add('show');
            }, 10);
            
            // 3秒後に非表示
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 300);
            }, 3000);
        };
    }
    
    // 既存のイベントリスナーをオーバーライド
    const updateBtn = document.getElementById('check-update-link');
    if (updateBtn) {
        // 既存のイベントリスナーをクリア
        const newBtn = updateBtn.cloneNode(true);
        updateBtn.parentNode.replaceChild(newBtn, updateBtn);
        
        // 新しいイベントリスナーを追加
        newBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('更新確認ボタンがクリックされました');
            
            // モーダルを直接表示
            try {
                const updateModal = document.getElementById('updateModal');
                if (updateModal) {
                    // Bootstrapのモーダルを初期化して表示
                    if (typeof jQuery !== 'undefined' && typeof jQuery.fn.modal !== 'undefined') {
                        $('#updateModal').modal('show');
                    } else {
                        // jQueryが利用できない場合はCSSでモーダルを表示
                        updateModal.style.display = 'block';
                        updateModal.classList.add('show');
                        updateModal.setAttribute('aria-hidden', 'false');
                        document.body.classList.add('modal-open');
                        
                        // 背景のオーバーレイを作成
                        const backdrop = document.createElement('div');
                        backdrop.className = 'modal-backdrop fade show';
                        document.body.appendChild(backdrop);
                    }
                    
                    // ステータス表示を更新
                    const statusMsg = document.getElementById('update-status-message');
                    if (statusMsg) {
                        statusMsg.textContent = '更新を確認中...';
                    }
                    
                    // 更新確認APIを実際に呼び出し
                    fetch('/api/check_updates', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                        },
                        body: JSON.stringify({})
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('APIサーバーからエラーレスポンス: ' + response.status);
                        }
                        return response.json();
                    })
                    .then(data => {
                        // ステータスメッセージ要素
                        const statusMsg = document.getElementById('update-status-message');
                        if (!statusMsg) {
                            console.error('update-status-message要素が見つかりません');
                            return;
                        }
                        
                        // 更新ボタン要素
                        const updateStartBtn = document.getElementById('update-start-btn');
                        if (!updateStartBtn) {
                            console.error('update-start-btn要素が見つかりません');
                            return;
                        }
                        
                        // アップデートが利用可能な場合
                        if (data.update_available === true) {
                            const message = data.message || `新しいバージョン ${data.latest_version} が利用可能です（現在のバージョン: ${data.current_version}）`;
                            statusMsg.textContent = message;
                            statusMsg.classList.remove('text-danger');
                            updateStartBtn.style.display = 'block';
                            console.log('更新ボタンを表示しました');
                        } 
                        // 正常だが更新なしの場合
                        else if (data.status === 'success' || data.status === '最新バージョンを使用中です') {
                            statusMsg.textContent = '最新バージョンを使用中です';
                            statusMsg.classList.remove('text-danger');
                            updateStartBtn.style.display = 'none';
                        }
                        // エラーの場合
                        else {
                            statusMsg.textContent = `エラー: ${data.status || data.message || '不明なエラー'}`;
                            statusMsg.classList.add('text-danger');
                            updateStartBtn.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('更新確認中にエラーが発生:', error);
                        if (statusMsg) {
                            statusMsg.textContent = `エラー: ${error.message}`;
                        }
                    });
                }
            } catch (error) {
                console.error('モーダル表示エラー:', error);
            }
        });
    }
    
    // 全データクリアリンクのイベントリスナーを修正
    const clearDataLink = document.getElementById('clear-all-data-link');
    if (clearDataLink) {
        // 既存のイベントリスナーをクリア
        const newLink = clearDataLink.cloneNode(true);
        clearDataLink.parentNode.replaceChild(newLink, clearDataLink);
        
        // 新しいイベントリスナーを追加
        newLink.addEventListener('click', function(e) {
            e.preventDefault();
            // モーダルを表示
            if (typeof jQuery !== 'undefined' && typeof jQuery.fn.modal !== 'undefined') {
                $('#clearAllDataModal').modal('show');
            }
        });
    }
    
    // 新規情報取得ボタンのイベントリスナーを修正
    const fetchButton = document.querySelector('.btn-fetch');
    if (fetchButton) {
        // 既存のイベントリスナーをクリア
        const newButton = fetchButton.cloneNode(true);
        fetchButton.parentNode.replaceChild(newButton, fetchButton);
        
        // 新しいイベントリスナーを追加
        newButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('新規情報の取得ボタンがクリックされました');
            
            // プログレスバーを表示
            const progressContainer = document.querySelector('.progress-container');
            if (progressContainer) {
                progressContainer.style.visibility = 'visible';
            }
            
            // 処理中の表示
            showToast('新規情報を取得中です...', 'info');
            
            // CSRFトークンの取得
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                             document.querySelector('meta[name="csrf-token"]')?.content;
            
            // 新規データ取得APIを呼び出し
            fetch('/fetch_new_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify({})
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('APIサーバーからエラーレスポンス: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                // プログレスバーを非表示
                if (progressContainer) {
                    progressContainer.style.visibility = 'hidden';
                }
                
                if (data.status === 'success') {
                    // 成功時のメッセージ表示
                    showToast(data.message, 'success');
                    console.log('新規データ取得成功:', data);
                    
                    // テーブルを更新する関数を呼び出し
                    if (typeof updateJobsTable === 'function') {
                        updateJobsTable(data.jobs);
                    } else {
                        console.error('updateJobsTable関数が定義されていません');
                        // 代替手段：ページをリロード
                        window.location.reload();
                    }
                } else {
                    showToast('エラー: ' + (data.message || '不明なエラー'), 'error');
                }
            })
            .catch(error => {
                // プログレスバーを非表示
                if (progressContainer) {
                    progressContainer.style.visibility = 'hidden';
                }
                console.error('データ取得中にエラーが発生:', error);
                showToast('データ取得に失敗しました: ' + error.message, 'error');
            });
        });
    }
    
    // 一括応募ボタンのイベントリスナーを修正
    const bulkApplyBtn = document.getElementById('bulk-apply-btn');
    if (bulkApplyBtn) {
        // 既存のイベントリスナーをクリア
        const newBulkApplyBtn = bulkApplyBtn.cloneNode(true);
        bulkApplyBtn.parentNode.replaceChild(newBulkApplyBtn, bulkApplyBtn);
        
        // 新しいイベントリスナーを追加
        newBulkApplyBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('一括応募ボタンがクリックされました');
            
            // チェックされた案件のURLを収集
            const checkedUrls = [];
            document.querySelectorAll('.job-check:checked').forEach(checkbox => {
                // data-url属性からURLを取得
                const url = checkbox.getAttribute('data-url');
                console.log('チェックされた案件のURL:', url);
                if (url) {
                    checkedUrls.push(url);
                }
            });
            
            console.log('応募する案件のURL一覧:', checkedUrls);
            
            if (checkedUrls.length === 0) {
                showToast('応募する案件が選択されていません', 'warning');
                return;
            }
            
            // 処理中の表示
            showToast(`${checkedUrls.length}件の案件に応募中...`, 'info');
            
            // プログレスバーを表示
            const progressContainer = document.querySelector('.progress-container');
            if (progressContainer) {
                progressContainer.style.display = 'block';
                const progressBar = progressContainer.querySelector('.progress-bar');
                const progressStatus = progressContainer.querySelector('.progress-status');
                
                if (progressBar) {
                    progressBar.style.width = '0%';
                    progressBar.setAttribute('aria-valuenow', '0');
                    progressBar.textContent = '0%';
                }
                
                if (progressStatus) {
                    progressStatus.textContent = '処理を開始しています...';
                }
            }
            
            // CSRFトークンの取得
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                             document.querySelector('meta[name="csrf-token"]')?.content;
            
            // 一括応募APIを呼び出し
            fetch('/bulk_apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify({
                    urls: checkedUrls
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('APIサーバーからエラーレスポンス: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    console.log('一括応募開始成功:', data);
                    
                    // プログレスの監視を開始
                    startProgressMonitoring();
                } else {
                    showToast('エラー: ' + (data.message || '不明なエラー'), 'error');
                    
                    // プログレスバーを非表示
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                }
            })
            .catch(error => {
                console.error('一括応募処理中にエラーが発生:', error);
                showToast('一括応募に失敗しました: ' + error.message, 'error');
                
                // プログレスバーを非表示
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
            });
        });
    }
    
    // 進捗状況の監視
    function startProgressMonitoring() {
        // Server-Sent Eventsを使用して進捗状況を監視
        const eventSource = new EventSource('/bulk_apply_progress');
        const progressContainer = document.querySelector('.progress-container');
        const progressBar = progressContainer?.querySelector('.progress-bar');
        const progressStatus = progressContainer?.querySelector('.progress-status');
        
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('進捗状況:', data);
                
                // プログレスバーを更新
                if (progressBar) {
                    const percent = Math.round(data.progress_percent || 0);
                    progressBar.style.width = `${percent}%`;
                    progressBar.setAttribute('aria-valuenow', percent);
                    progressBar.textContent = `${percent}%`;
                }
                
                // ステータスメッセージを更新
                if (progressStatus) {
                    progressStatus.textContent = data.message || '処理中...';
                }
                
                // 完了したら接続を閉じる
                if (data.completed) {
                    eventSource.close();
                    
                    // 成功時と失敗時で処理を分ける
                    if (data.status === 'success') {
                        showToast('一括応募が完了しました', 'success');
                    } else if (data.status === 'error') {
                        showToast('一括応募中にエラーが発生しました: ' + data.message, 'error');
                    }
                    
                    // しばらくしてからプログレスバーを非表示
                    setTimeout(() => {
                        if (progressContainer) {
                            progressContainer.style.display = 'none';
                        }
                    }, 3000);
                }
            } catch (error) {
                console.error('進捗データの解析に失敗:', error);
                
                // エラー時は接続を閉じる
                eventSource.close();
                
                if (progressStatus) {
                    progressStatus.textContent = 'エラーが発生しました';
                }
                
                // プログレスバーを非表示
                setTimeout(() => {
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                }, 3000);
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('SSE接続エラー:', error);
            eventSource.close();
            
            if (progressStatus) {
                progressStatus.textContent = '接続エラーが発生しました';
            }
            
            // プログレスバーを非表示
            setTimeout(() => {
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
            }, 3000);
        };
    }
    
    // トースト表示用のスタイルを追加
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.innerHTML = `
            .toast-notification {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 4px;
                color: white;
                font-size: 14px;
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
                max-width: 300px;
                box-shadow: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
            }
            .toast-notification.show {
                opacity: 1;
            }
            .toast-success {
                background-color: #4CAF50;
            }
            .toast-error {
                background-color: #F44336;
            }
            .toast-warning {
                background-color: #FF9800;
            }
            .toast-info {
                background-color: #2196F3;
            }
        `;
        document.head.appendChild(style);
    }
}); 