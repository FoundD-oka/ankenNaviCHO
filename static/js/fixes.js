// 更新確認ボタンのアラートを削除するスクリプト
document.addEventListener('DOMContentLoaded', function() {
    // トースト表示関数がグローバルに定義されていない場合は定義する
    if (typeof window.showToast !== 'function') {
        window.showToast = function(message, type) {
            console.log(`Toast (${type}): ${message}`);
            
            // 既存のトーストを削除
            const existingToasts = document.querySelectorAll('.toast-notification');
            existingToasts.forEach(toast => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            });
            
            const toast = document.createElement('div');
            toast.className = `toast-notification toast-${type}`;
            toast.innerHTML = message;
            document.body.appendChild(toast);
            
            // タイムアウトIDを保存するための属性を追加
            toast.setAttribute('data-timeout-id', '');
            
            console.log('トースト要素を作成しました:', toast);
            
            // 表示のタイミングを少し遅らせる
            setTimeout(() => {
                toast.classList.add('show');
                console.log('トーストにshowクラスを追加しました');
                
                // 一定時間後に非表示
                const timeoutId = setTimeout(() => {
                    toast.classList.remove('show');
                    console.log('トーストからshowクラスを削除しました');
                    setTimeout(() => {
                        if (document.body.contains(toast)) {
                            document.body.removeChild(toast);
                        }
                        console.log('トーストを削除しました');
                    }, 300);
                }, 3000);
                
                // タイムアウトIDを保存
                toast.setAttribute('data-timeout-id', timeoutId);
                
                // トーストをクリックしたら閉じる
                toast.addEventListener('click', () => {
                    // 設定したタイムアウトをクリア
                    clearTimeout(parseInt(toast.getAttribute('data-timeout-id')));
                    
                    // トーストを閉じる
                    toast.classList.remove('show');
                    setTimeout(() => {
                        if (document.body.contains(toast)) {
                            document.body.removeChild(toast);
                        }
                    }, 300);
                });
            }, 10);
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
            
            // ボタンを無効化
            this.disabled = true;
            this.classList.add('btn-disabled');
            
            // プログレスバーの要素を取得
            const progressContainer = document.getElementById('fetch-progress-container');
            const progressBarDiv = document.getElementById('progress-bar-div');
            const progressBar = document.getElementById('progress-bar');
            const progressStatus = document.getElementById('progress-status');
            
            // ダミープログレス用の変数を外側のスコープで宣言
            let dummyProgress = 0;
            let progressInterval = null;
            
            // プログレスバーを表示し初期化
            if (progressContainer) {
                console.log('プログレスバーコンテナを表示');
                progressContainer.style.display = 'block';
                
                if (progressBarDiv) {
                    progressBarDiv.style.width = '0%';
                    progressBarDiv.setAttribute('aria-valuenow', '0');
                }
                
                if (progressBar) {
                    progressBar.value = 0;
                    progressBar.setAttribute('aria-valuenow', '0');
                }
                
                if (progressStatus) {
                    progressStatus.textContent = '新着情報の取得中...';
                }
                
                // 案件数に基づくダミープログレス開始
                console.log('案件数に基づくダミープログレス開始');
                
                // 推定案件数を取得（APIから取得するか、UIから取得するか、固定値でもOK）
                // 例として、入力値または固定値を使用
                const maxItems = document.getElementById('max-items')?.value || 20;
                const entriesCount = parseInt(maxItems);
                console.log(`想定案件数: ${entriesCount}件`);
                
                // 1件あたりの想定処理時間（秒）- 調整可能
                const timePerEntrySec = 2.5;
                
                // 総推定時間をミリ秒で計算
                const estimatedTotalMs = entriesCount * timePerEntrySec * 1000;
                console.log(`推定総時間: ${estimatedTotalMs}ms (${estimatedTotalMs/1000}秒)`);
                
                // ダミーバーの最大は99%までとして、1msあたりの上昇率を計算
                const progressIncrementPerMs = 99 / estimatedTotalMs;
                console.log(`1msあたりの進行率: ${progressIncrementPerMs}`);
                
                progressInterval = setInterval(() => {
                    // 各インターバルでの増分を計算
                    const increment = progressIncrementPerMs * 100;
                    dummyProgress += increment;
                    
                    // 99%を超えないようにする
                    if (dummyProgress >= 99) {
                        dummyProgress = 99;
                        clearInterval(progressInterval);
                        progressInterval = null;
                    }
                    
                    // 5%単位で表示を更新（パフォーマンス改善と動きを見やすく）
                    const roundedValue = Math.floor(dummyProgress / 5) * 5;
                    
                    // 前回の値と同じなら更新しない
                    const currentValue = parseInt(progressBarDiv?.getAttribute('aria-valuenow') || '0');
                    if (roundedValue > currentValue) {
                        console.log(`ダミープログレス: ${roundedValue}%`);
                        
                        // プログレスバーの更新
                        if (progressBarDiv) {
                            progressBarDiv.style.width = `${roundedValue}%`;
                            progressBarDiv.setAttribute('aria-valuenow', roundedValue);
                        }
                        
                        if (progressBar) {
                            progressBar.value = roundedValue;
                            progressBar.setAttribute('aria-valuenow', roundedValue);
                        }
                        
                        // 進行状況に応じてメッセージを変更
                        if (progressStatus) {
                            if (roundedValue < 30) {
                                progressStatus.textContent = '新着情報の取得中...';
                            } else if (roundedValue < 60) {
                                progressStatus.textContent = '案件の分析中...';
                            } else if (roundedValue < 90) {
                                progressStatus.textContent = '案件の仕分け中...';
                            } else {
                                progressStatus.textContent = 'もう少しお待ちください...';
                            }
                        }
                    }
                }, 100);
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
                // ダミープログレスを停止
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                    console.log('ダミープログレス停止');
                }
                
                let finalStatusText = '';
                
                if (data.status === 'success') {
                    finalStatusText = '取得完了';
                    
                    // プログレスバーを100%にする
                    if (progressBarDiv) {
                        progressBarDiv.style.width = '100%';
                        progressBarDiv.setAttribute('aria-valuenow', '100');
                    }
                    
                    if (progressBar) {
                        progressBar.value = 100;
                        progressBar.setAttribute('aria-valuenow', '100');
                    }
                    
                    // 成功時のメッセージ表示
                    showToast(`案件データを ${data.jobs ? data.jobs.length : 0} 件更新しました`, 'success');
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
                    finalStatusText = 'エラー発生';
                    
                    // エラー時もプログレスバーを100%にする
                    if (progressBarDiv) {
                        progressBarDiv.style.width = '100%';
                        progressBarDiv.setAttribute('aria-valuenow', '100');
                    }
                    
                    if (progressBar) {
                        progressBar.value = 100;
                        progressBar.setAttribute('aria-valuenow', '100');
                    }
                    
                    showToast('エラー: ' + (data.message || '不明なエラー'), 'error');
                }
                
                if (progressStatus) {
                    progressStatus.textContent = finalStatusText;
                }
                
                // 少し待ってからプログレスバーを非表示にする
                setTimeout(() => {
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    
                    // ボタンを有効化
                    this.disabled = false;
                    this.classList.remove('btn-disabled');
                }, 1500);
            })
            .catch(error => {
                // ダミープログレスを停止
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
                
                // エラー時もプログレスバーを100%にする
                if (progressBarDiv) {
                    progressBarDiv.style.width = '100%';
                    progressBarDiv.setAttribute('aria-valuenow', '100');
                }
                
                if (progressBar) {
                    progressBar.value = 100;
                    progressBar.setAttribute('aria-valuenow', '100');
                }
                
                if (progressStatus) {
                    progressStatus.textContent = 'エラー発生';
                }
                
                console.error('データ取得中にエラーが発生:', error);
                showToast('データ取得に失敗しました: ' + error.message, 'error');
                
                // 少し待ってからプログレスバーを非表示にする
                setTimeout(() => {
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    
                    // ボタンを有効化
                    this.disabled = false;
                    this.classList.remove('btn-disabled');
                }, 1500);
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
            
            // 一括応募用のダミープログレス変数を外側のスコープで宣言
            let dummyProgress = 0;
            let initialProgressInterval = null;
            
            // プログレスバーを表示（一括応募ボタン下のプログレスバー）
            // 注意: このプログレスバーは新規情報取得のプログレスバーとは異なる
            const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
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

                // 選択された案件数に基づくダミープログレス（SSEが接続されるまでの間）
                const selectedCount = checkedUrls.length;
                console.log(`選択された案件数: ${selectedCount}件`);
                
                // 1件あたりの想定処理時間（秒）- 調整可能
                const timePerApplySec = 5; // 応募処理は取得より時間がかかると想定
                
                // SSE接続までの初期ダミー進行（全体の10%まで）
                const initialDummyDuration = Math.min(selectedCount * 500, 3000); // 最大3秒
                const initialIncrement = 10 / (initialDummyDuration / 100); // 10%まで上げる
                
                initialProgressInterval = setInterval(() => {
                    dummyProgress += initialIncrement;
                    if (dummyProgress >= 10) {
                        dummyProgress = 10;
                        clearInterval(initialProgressInterval);
                    }
                    
                    // 5%単位で表示を更新
                    const roundedValue = Math.floor(dummyProgress / 5) * 5;
                    const currentValue = parseInt(progressBar?.getAttribute('aria-valuenow') || '0');
                    
                    if (roundedValue > currentValue) {
                        console.log(`初期ダミープログレス: ${roundedValue}%`);
                        if (progressBar) {
                            progressBar.style.width = `${roundedValue}%`;
                            progressBar.setAttribute('aria-valuenow', roundedValue);
                            progressBar.textContent = `${roundedValue}%`;
                        }
                    }
                }, 100);
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
                    
                    // プログレスバーを非表示（一括応募ボタン下のプログレスバー）
                    const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                }
            })
            .catch(error => {
                console.error('一括応募処理中にエラーが発生:', error);
                showToast('一括応募に失敗しました: ' + error.message, 'error');
                
                // プログレスバーを非表示（一括応募ボタン下のプログレスバー）
                const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
            });
        });
    }
    
    // 進捗状況の監視と変数のグローバル宣言（関数内でのスコープエラー対策）
    let monitorFallbackInterval = null;
    let monitorDummyProgress = 0;
    
    function startProgressMonitoring() {
        // Server-Sent Eventsを使用して進捗状況を監視
        const eventSource = new EventSource('/bulk_apply_progress');
        const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
        const progressBar = progressContainer?.querySelector('.progress-bar');
        const progressStatus = progressContainer?.querySelector('.progress-status');
        
        // ダミープログレスの変数とタイマー（SSEが接続されるまでの間）
        monitorDummyProgress = parseFloat(progressBar?.getAttribute('aria-valuenow') || '0');
        let sseConnected = false;
        
        // SSE接続までのフォールバックダミー進行
        if (monitorDummyProgress < 80) {
            // 10%→80%までを約30秒かけて徐々に進める（SSEが来なかった場合用）
            const remainingProgress = 80 - monitorDummyProgress;
            const fallbackDuration = 30000; // 30秒
            const incrementPerStep = remainingProgress / (fallbackDuration / 100);
            
            monitorFallbackInterval = setInterval(() => {
                // SSEが接続されたら停止
                if (sseConnected) {
                    if (monitorFallbackInterval) {
                        clearInterval(monitorFallbackInterval);
                        monitorFallbackInterval = null;
                    }
                    return;
                }
                
                monitorDummyProgress += incrementPerStep;
                if (monitorDummyProgress >= 80) {
                    monitorDummyProgress = 80;
                    if (monitorFallbackInterval) {
                        clearInterval(monitorFallbackInterval);
                        monitorFallbackInterval = null;
                    }
                }
                
                // 5%単位で表示を更新
                const roundedValue = Math.floor(monitorDummyProgress / 5) * 5;
                const currentValue = parseInt(progressBar?.getAttribute('aria-valuenow') || '0');
                
                if (roundedValue > currentValue) {
                    console.log(`フォールバックダミープログレス: ${roundedValue}%`);
                    if (progressBar) {
                        progressBar.style.width = `${roundedValue}%`;
                        progressBar.setAttribute('aria-valuenow', roundedValue);
                        progressBar.textContent = `${roundedValue}%`;
                    }
                    
                    // 進行状況に応じてテキストを変更
                    if (progressStatus) {
                        if (roundedValue < 30) {
                            progressStatus.textContent = '応募処理を開始しています...';
                        } else if (roundedValue < 60) {
                            progressStatus.textContent = '応募データを送信中...';
                        } else {
                            progressStatus.textContent = '応募処理を実行中...';
                        }
                    }
                }
            }, 100);
        }
        
        // SSEメッセージの処理
        eventSource.onmessage = function(event) {
            try {
                // SSE接続フラグをオン
                sseConnected = true;
                
                // フォールバックインターバルが動いていたら停止
                if (monitorFallbackInterval) {
                    clearInterval(monitorFallbackInterval);
                    monitorFallbackInterval = null;
                }
                
                const data = JSON.parse(event.data);
                console.log('進捗状況:', data);
                
                // プログレスバーを更新
                if (progressBar) {
                    const percent = Math.round(data.progress_percent || 0);
                    // 現在の値より小さい場合は更新しない（後退して見えるのを防止）
                    const currentPercent = parseInt(progressBar.getAttribute('aria-valuenow') || '0');
                    if (percent > currentPercent) {
                        progressBar.style.width = `${percent}%`;
                        progressBar.setAttribute('aria-valuenow', percent);
                        progressBar.textContent = `${percent}%`;
                        
                        // ダミー進行の現在値も更新（フォールバック用）
                        monitorDummyProgress = percent;
                    }
                }
                
                // ステータスメッセージを更新
                if (progressStatus && data.message) {
                    progressStatus.textContent = data.message;
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
                    
                    // プログレスバーを100%にする
                    if (progressBar) {
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressBar.textContent = '100%';
                    }
                    
                    // しばらくしてからプログレスバーを非表示
                    setTimeout(() => {
                        // 一括応募ボタン下のプログレスバーを非表示
                        const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
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
            
            // 3回までリトライする仕組みを追加
            const maxRetries = 3;
            const retryCount = parseInt(eventSource.getAttribute('data-retry-count') || '0');
            
            if (retryCount < maxRetries) {
                console.log(`SSE接続をリトライします (${retryCount + 1}/${maxRetries})`);
                eventSource.setAttribute('data-retry-count', (retryCount + 1).toString());
                // リトライは自動的に行われる
                
                if (progressStatus) {
                    progressStatus.textContent = `接続をリトライしています (${retryCount + 1}/${maxRetries})...`;
                }
            } else {
                // リトライ回数を超えたら接続を閉じる
                eventSource.close();
                
                if (progressStatus) {
                    progressStatus.textContent = '接続エラーが発生しました。処理は継続されています...';
                }
                
                // フォールバックのダミー進行を続ける（接続エラーでも処理は続いている可能性）
                // 何もしない（monitorFallbackIntervalはそのまま動き続ける）
                
                // 60秒後に強制的に完了したとみなす（最悪のフォールバック）
                setTimeout(() => {
                    // 最終的なフォールバック（実際の処理は完了していると仮定）
                    if (monitorFallbackInterval) {
                        clearInterval(monitorFallbackInterval);
                        monitorFallbackInterval = null;
                    }
                    
                    showToast('応募処理が完了したとみなします', 'info');
                    
                    // プログレスバーを100%にする
                    if (progressBar) {
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressBar.textContent = '100%';
                    }
                    
                    // しばらくしてからプログレスバーを非表示
                    setTimeout(() => {
                        const progressContainer = document.querySelector('.bulk-apply-container .progress-container');
                        if (progressContainer) {
                            progressContainer.style.display = 'none';
                        }
                    }, 3000);
                }, 60000);
                
                // エラーメッセージを表示
                showToast('進捗状況の取得に失敗しましたが、処理は継続しています', 'warning');
            }
        };
    }
    
    // トースト表示用のスタイルを追加
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.innerHTML = `
            .toast-notification {
                position: fixed;
                top: 20px;
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
                display: block;
            }
            .toast-notification.show {
                opacity: 1;
            }
            .toast-success {
                background-color: #4CAF50;
                border-left: 4px solid #2E7D32;
            }
            .toast-error {
                background-color: #F44336;
                border-left: 4px solid #C62828;
            }
            .toast-warning {
                background-color: #FF9800;
                border-left: 4px solid #EF6C00;
            }
            .toast-info {
                background-color: #2196F3;
                border-left: 4px solid #1565C0;
            }
        `;
        document.head.appendChild(style);
    }
    
    // プログレスバーの高さ調整用スタイルを追加
    if (!document.getElementById('progress-styles')) {
        const progressStyle = document.createElement('style');
        progressStyle.id = 'progress-styles';
        progressStyle.innerHTML = `
            /* プログレスバーの高さを半分に */
            .progress {
                height: 16px !important;
            }
            .progress-bar {
                height: 16px !important;
                line-height: 16px !important;
                font-size: 12px !important;
            }
            /* 特定の場所のプログレスバーのスタイル調整 */
            #fetch-progress-container .progress {
                height: 16px !important;
            }
            #fetch-progress-container .progress-bar {
                height: 16px !important;
            }
            .bulk-apply-container .progress {
                height: 16px !important;
            }
            .bulk-apply-container .progress-bar {
                height: 16px !important;
            }
        `;
        document.head.appendChild(progressStyle);
    }
}); 