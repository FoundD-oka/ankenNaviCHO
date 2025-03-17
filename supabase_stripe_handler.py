import os
import json
import stripe
from datetime import datetime
from supabase import create_client, Client

# Supabase設定
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Stripe設定
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Supabaseクライアント初期化
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Stripe初期化
stripe.api_key = STRIPE_SECRET_KEY

class StripeHandler:
    @staticmethod
    def create_customer(user_id, email, name=None):
        """
        Stripeで顧客を作成し、Supabaseのユーザーと紐付ける
        """
        try:
            # Stripe顧客作成
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            
            # Supabaseユーザー更新
            supabase.table("users").update({
                "stripe_customer_id": customer.id
            }).eq("id", user_id).execute()
            
            return customer.id
        except Exception as e:
            print(f"Stripe顧客作成エラー: {str(e)}")
            return None
    
    @staticmethod
    def create_subscription(user_id, product_id, payment_method_id=None):
        """
        ユーザーのサブスクリプションを作成する
        """
        try:
            # ユーザー情報取得
            user_response = supabase.table("users").select("*").eq("id", user_id).execute()
            if not user_response.data:
                return {"error": "ユーザーが見つかりません"}
            
            user = user_response.data[0]
            stripe_customer_id = user.get("stripe_customer_id")
            
            # 顧客IDがない場合は作成
            if not stripe_customer_id:
                return {"error": "Stripe顧客IDがありません"}
            
            # 商品情報取得
            product_response = supabase.table("products").select("*").eq("id", product_id).execute()
            if not product_response.data:
                return {"error": "商品が見つかりません"}
            
            product = product_response.data[0]
            
            # サブスクリプションでない場合はエラー
            if not product.get("is_subscription"):
                return {"error": "選択された商品はサブスクリプションではありません"}
            
            # 支払い方法が指定されている場合は顧客のデフォルト支払い方法として設定
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=stripe_customer_id
                )
                
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )
            
            # サブスクリプション作成
            subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[{
                    "price": product.get("stripe_product_id")  # Stripeの価格ID
                }],
                expand=["latest_invoice.payment_intent"],
                metadata={
                    "user_id": user_id,
                    "product_id": product_id
                }
            )
            
            # Supabaseにサブスクリプション情報を保存
            subscription_data = {
                "user_id": user_id,
                "product_id": product_id,
                "stripe_subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "metadata": json.dumps(subscription.metadata)
            }
            
            subscription_response = supabase.table("subscriptions").insert(subscription_data).execute()
            
            # 最初の請求書があれば支払い履歴に記録
            if hasattr(subscription, "latest_invoice") and subscription.latest_invoice:
                invoice = subscription.latest_invoice
                payment_intent = invoice.payment_intent if hasattr(invoice, "payment_intent") else None
                
                payment_data = {
                    "user_id": user_id,
                    "product_id": product_id,
                    "subscription_id": subscription_response.data[0]["id"],
                    "stripe_invoice_id": invoice.id,
                    "amount": invoice.amount_due,
                    "status": invoice.status,
                    "payment_method": payment_intent.payment_method if payment_intent else None,
                    "stripe_payment_intent_id": payment_intent.id if payment_intent else None,
                    "paid_at": datetime.fromtimestamp(invoice.status_transitions.paid_at) if hasattr(invoice.status_transitions, "paid_at") else None,
                    "metadata": json.dumps({"invoice_id": invoice.id})
                }
                
                supabase.table("payment_history").insert(payment_data).execute()
            
            return {"subscription_id": subscription.id, "status": subscription.status}
        
        except Exception as e:
            print(f"サブスクリプション作成エラー: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def create_checkout_session(user_id, product_id, success_url, cancel_url):
        """
        商品購入用のStripeチェックアウトセッションを作成
        """
        try:
            # ユーザー情報取得
            user_response = supabase.table("users").select("*").eq("id", user_id).execute()
            if not user_response.data:
                return {"error": "ユーザーが見つかりません"}
            
            user = user_response.data[0]
            stripe_customer_id = user.get("stripe_customer_id")
            
            # 顧客IDがない場合は作成
            if not stripe_customer_id:
                return {"error": "Stripe顧客IDがありません"}
            
            # 商品情報取得
            product_response = supabase.table("products").select("*").eq("id", product_id).execute()
            if not product_response.data:
                return {"error": "商品が見つかりません"}
            
            product = product_response.data[0]
            
            # セッションの作成
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': product.get("stripe_product_id"),
                    'quantity': 1,
                }],
                mode='payment' if not product.get("is_subscription") else 'subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                    "product_id": product_id
                }
            )
            
            return {"session_id": checkout_session.id, "url": checkout_session.url}
        
        except Exception as e:
            print(f"チェックアウトセッション作成エラー: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def handle_webhook(payload, sig_header):
        """
        Stripeウェブフックを処理する
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            
            # イベントタイプに基づいて処理
            event_type = event['type']
            data = event['data']['object']
            
            if event_type == 'checkout.session.completed':
                # チェックアウト完了時の処理
                handle_checkout_completed(data)
            
            elif event_type == 'invoice.paid':
                # 請求書支払い完了時の処理
                handle_invoice_paid(data)
            
            elif event_type == 'invoice.payment_failed':
                # 請求書支払い失敗時の処理
                handle_invoice_payment_failed(data)
            
            elif event_type == 'customer.subscription.updated':
                # サブスクリプション更新時の処理
                handle_subscription_updated(data)
            
            elif event_type == 'customer.subscription.deleted':
                # サブスクリプション削除時の処理
                handle_subscription_deleted(data)
            
            return {"success": True}
        
        except Exception as e:
            print(f"ウェブフック処理エラー: {str(e)}")
            return {"error": str(e)}

def handle_checkout_completed(session):
    """
    チェックアウト完了時の処理
    """
    try:
        user_id = session.get('metadata', {}).get('user_id')
        product_id = session.get('metadata', {}).get('product_id')
        
        if not user_id or not product_id:
            print("メタデータにuser_idまたはproduct_idが見つかりません")
            return
        
        # 商品情報取得
        product_response = supabase.table("products").select("*").eq("id", product_id).execute()
        if not product_response.data:
            print(f"商品が見つかりません: {product_id}")
            return
        
        product = product_response.data[0]
        
        # サブスクリプションの場合は処理しない（別のイベントで処理）
        if product.get("is_subscription"):
            return
        
        # 支払い情報の取得
        if session.get('payment_intent'):
            payment_intent = stripe.PaymentIntent.retrieve(session.get('payment_intent'))
            
            # 購入レコード作成
            purchase_data = {
                "user_id": user_id,
                "product_id": product_id,
                "stripe_payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "status": payment_intent.status,
                "metadata": json.dumps(payment_intent.metadata)
            }
            
            purchase_response = supabase.table("purchases").insert(purchase_data).execute()
            
            # 支払い履歴に記録
            payment_data = {
                "user_id": user_id,
                "product_id": product_id,
                "purchase_id": purchase_response.data[0]["id"],
                "stripe_payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "status": payment_intent.status,
                "payment_method": payment_intent.payment_method,
                "paid_at": datetime.now(),
                "metadata": json.dumps({"session_id": session.id})
            }
            
            supabase.table("payment_history").insert(payment_data).execute()
    
    except Exception as e:
        print(f"チェックアウト完了処理エラー: {str(e)}")

def handle_invoice_paid(invoice):
    """
    請求書支払い完了時の処理
    """
    try:
        if not invoice.get('subscription'):
            return
        
        # サブスクリプション情報を取得
        subscription = stripe.Subscription.retrieve(invoice.get('subscription'))
        user_id = subscription.get('metadata', {}).get('user_id')
        product_id = subscription.get('metadata', {}).get('product_id')
        
        if not user_id or not product_id:
            # サブスクリプションからメタデータが取得できない場合、DBから検索
            subscription_response = supabase.table("subscriptions").select("*").eq("stripe_subscription_id", invoice.get('subscription')).execute()
            if subscription_response.data:
                user_id = subscription_response.data[0].get("user_id")
                product_id = subscription_response.data[0].get("product_id")
                subscription_id = subscription_response.data[0].get("id")
            else:
                print(f"サブスクリプションが見つかりません: {invoice.get('subscription')}")
                return
        else:
            # サブスクリプションIDをDBから取得
            subscription_response = supabase.table("subscriptions").select("*").eq("stripe_subscription_id", subscription.id).execute()
            subscription_id = subscription_response.data[0].get("id") if subscription_response.data else None
        
        # 支払い履歴に記録
        payment_data = {
            "user_id": user_id,
            "product_id": product_id,
            "subscription_id": subscription_id,
            "stripe_invoice_id": invoice.id,
            "amount": invoice.amount_paid,
            "status": invoice.status,
            "payment_method": invoice.payment_intent.payment_method if invoice.payment_intent else None,
            "stripe_payment_intent_id": invoice.payment_intent if invoice.payment_intent else None,
            "paid_at": datetime.fromtimestamp(invoice.status_transitions.paid_at) if hasattr(invoice.status_transitions, "paid_at") else datetime.now(),
            "metadata": json.dumps({"invoice_id": invoice.id})
        }
        
        supabase.table("payment_history").insert(payment_data).execute()
        
        # サブスクリプションステータス更新
        if subscription_id:
            supabase.table("subscriptions").update({
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "updated_at": datetime.now()
            }).eq("id", subscription_id).execute()
    
    except Exception as e:
        print(f"請求書支払い完了処理エラー: {str(e)}")

def handle_invoice_payment_failed(invoice):
    """
    請求書支払い失敗時の処理
    """
    try:
        if not invoice.get('subscription'):
            return
        
        # サブスクリプション情報を取得
        subscription_response = supabase.table("subscriptions").select("*").eq("stripe_subscription_id", invoice.get('subscription')).execute()
        if not subscription_response.data:
            print(f"サブスクリプションが見つかりません: {invoice.get('subscription')}")
            return
        
        subscription_id = subscription_response.data[0].get("id")
        user_id = subscription_response.data[0].get("user_id")
        product_id = subscription_response.data[0].get("product_id")
        
        # サブスクリプションのステータスを更新
        supabase.table("subscriptions").update({
            "status": "past_due",
            "updated_at": datetime.now()
        }).eq("id", subscription_id).execute()
        
        # 支払い履歴に記録
        payment_data = {
            "user_id": user_id,
            "product_id": product_id,
            "subscription_id": subscription_id,
            "stripe_invoice_id": invoice.id,
            "amount": invoice.amount_due,
            "status": "failed",
            "payment_method": invoice.payment_intent.payment_method if invoice.payment_intent else None,
            "stripe_payment_intent_id": invoice.payment_intent if invoice.payment_intent else None,
            "metadata": json.dumps({"invoice_id": invoice.id, "failure_message": invoice.get("last_payment_error", {}).get("message")})
        }
        
        supabase.table("payment_history").insert(payment_data).execute()
    
    except Exception as e:
        print(f"請求書支払い失敗処理エラー: {str(e)}")

def handle_subscription_updated(subscription):
    """
    サブスクリプション更新時の処理
    """
    try:
        # サブスクリプション情報をDBから取得
        subscription_response = supabase.table("subscriptions").select("*").eq("stripe_subscription_id", subscription.id).execute()
        if not subscription_response.data:
            print(f"サブスクリプションが見つかりません: {subscription.id}")
            return
        
        subscription_id = subscription_response.data[0].get("id")
        
        # サブスクリプションステータス更新
        supabase.table("subscriptions").update({
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            "cancel_at": datetime.fromtimestamp(subscription.cancel_at) if subscription.cancel_at else None,
            "canceled_at": datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
            "updated_at": datetime.now()
        }).eq("id", subscription_id).execute()
    
    except Exception as e:
        print(f"サブスクリプション更新処理エラー: {str(e)}")

def handle_subscription_deleted(subscription):
    """
    サブスクリプション削除時の処理
    """
    try:
        # サブスクリプション情報をDBから取得
        subscription_response = supabase.table("subscriptions").select("*").eq("stripe_subscription_id", subscription.id).execute()
        if not subscription_response.data:
            print(f"サブスクリプションが見つかりません: {subscription.id}")
            return
        
        subscription_id = subscription_response.data[0].get("id")
        
        # サブスクリプションステータス更新
        supabase.table("subscriptions").update({
            "status": "canceled",
            "canceled_at": datetime.now(),
            "updated_at": datetime.now()
        }).eq("id", subscription_id).execute()
    
    except Exception as e:
        print(f"サブスクリプション削除処理エラー: {str(e)}")

# ユーティリティ関数
def get_user_subscriptions(user_id):
    """
    ユーザーのサブスクリプション一覧を取得
    """
    try:
        response = supabase.table("subscriptions").select(
            "*, products(name, description, price, is_subscription, interval, features)"
        ).eq("user_id", user_id).execute()
        
        return response.data
    except Exception as e:
        print(f"サブスクリプション取得エラー: {str(e)}")
        return []

def get_user_purchases(user_id):
    """
    ユーザーの購入履歴を取得
    """
    try:
        response = supabase.table("purchases").select(
            "*, products(name, description, price, is_subscription)"
        ).eq("user_id", user_id).execute()
        
        return response.data
    except Exception as e:
        print(f"購入履歴取得エラー: {str(e)}")
        return []

def get_user_payment_history(user_id):
    """
    ユーザーの支払い履歴を取得
    """
    try:
        response = supabase.table("payment_history").select(
            "*, products(name, price), subscriptions(id, stripe_subscription_id), purchases(id, stripe_payment_intent_id)"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return response.data
    except Exception as e:
        print(f"支払い履歴取得エラー: {str(e)}")
        return []

def cancel_subscription(subscription_id, cancel_immediately=False):
    """
    サブスクリプションをキャンセルする
    """
    try:
        # サブスクリプション情報をDBから取得
        subscription_response = supabase.table("subscriptions").select("*").eq("id", subscription_id).execute()
        if not subscription_response.data:
            return {"error": "サブスクリプションが見つかりません"}
        
        stripe_subscription_id = subscription_response.data[0].get("stripe_subscription_id")
        
        # Stripeでサブスクリプションをキャンセル
        if cancel_immediately:
            stripe.Subscription.delete(stripe_subscription_id)
        else:
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
        
        return {"success": True, "message": "サブスクリプションをキャンセルしました"}
    
    except Exception as e:
        print(f"サブスクリプションキャンセルエラー: {str(e)}")
        return {"error": str(e)} 