// 更新確認ボタンのアラートを削除するスクリプト
document.addEventListener('DOMContentLoaded', function() {
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
                        if (data.status === 'success') {
                            if (data.update_available) {
                                // 更新が利用可能な場合
                                statusMsg.textContent = 
                                    `新しいバージョン ${data.latest_version} が利用可能です（現在のバージョン: ${data.current_version}）`;
                                document.getElementById('update-start-btn').style.display = 'block';
                            } else {
                                // 更新がない場合
                                statusMsg.textContent = '最新バージョンを使用中です';
                            }
                        } else {
                            // エラーの場合
                            statusMsg.textContent = `エラー: ${data.status || data.message || '不明なエラー'}`;
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
}); 