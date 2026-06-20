import csv
from datetime import datetime
from io import StringIO
from flask import Blueprint, render_template, request, Response, jsonify, current_app, redirect, url_for, flash

from smart_rbac.models import AuditLog, BehaviorAlert, RiskScore, User
from smart_rbac.utils.auth_helper import login_required, permission_required, get_current_user

telemetry_bp = Blueprint('telemetry', __name__)

@telemetry_bp.route('/logs', methods=['GET'])
@login_required
@permission_required('view_audit_logs')
def logs_trail():
    """Display audit logs with filtering and searching capabilities."""
    search_query = request.args.get('search', '').strip()
    action_filter = request.args.get('action', '').strip()
    
    audit_records = AuditLog.get_all()
    
    if search_query:
        query_lower = search_query.lower()
        audit_records = [
            log for log in audit_records
            if (log.username and query_lower in log.username.lower()) or
               (log.action and query_lower in log.action.lower()) or
               (log.ip_address and query_lower in log.ip_address.lower())
        ]
    if action_filter:
        audit_records = [
            log for log in audit_records
            if log.action == action_filter
        ]
        
    audit_records.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
    
    # Get distinct action types for filter dropdown
    all_logs = AuditLog.get_all()
    distinct_actions = sorted(list(set(log.action for log in all_logs if log.action)))
    
    return render_template(
        'logs.html', 
        logs=audit_records, 
        distinct_actions=distinct_actions,
        search_query=search_query,
        action_filter=action_filter
    )


@telemetry_bp.route('/logs/export', methods=['GET'])
@login_required
@permission_required('view_audit_logs')
def export_logs_csv():
    """Export the system audit trails to compliance CSV format."""
    audit_records = AuditLog.get_all()
    audit_records.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
    
    si = StringIO()
    cw = csv.writer(si)
    
    # Write CSV Header
    cw.writerow(['ID', 'Username', 'Action Taken', 'Source IP Address', 'UTC Timestamp'])
    
    # Write CSV Rows
    for log in audit_records:
        cw.writerow([
            log.id,
            log.username,
            log.action,
            log.ip_address,
            log.timestamp.isoformat() if hasattr(log.timestamp, 'isoformat') else str(log.timestamp or '')
        ])
        
    response = Response(si.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=cyber_shield_audit_logs.csv'
    return response


@telemetry_bp.route('/analytics', methods=['GET'])
@login_required
@permission_required('view_analytics')
def threat_analytics():
    """Display Behavior Alerts and UBA telemetry dashboard."""
    alerts = BehaviorAlert.get_all()
    alerts.sort(key=lambda x: x.triggered_at or datetime.min, reverse=True)
    
    # High risk score logins count
    high_risk_count = sum(1 for rs in RiskScore.get_all() if rs.risk_level == 'High')
    
    # Locked/suspended account count
    locked_count = sum(1 for u in User.get_all() if u.status == 'suspended')
    
    return render_template(
        'analytics.html', 
        alerts=alerts, 
        high_risk_count=high_risk_count,
        locked_count=locked_count
    )


@telemetry_bp.route('/analytics/resolve-alert/<string:alert_id>', methods=['POST'])
@login_required
@permission_required('view_analytics')
def resolve_alert(alert_id):
    """Resolve an open behavior security alert."""
    admin_user = get_current_user()
    alert = BehaviorAlert.get(alert_id)
    if not alert:
        flash("Alert not found.", "danger")
        return redirect(url_for('telemetry.threat_analytics'))
        
    try:
        alert.status = 'resolved'
        alert.save()
        
        audit = AuditLog(
            username=admin_user.username,
            action=f"SECURITY_ALERT_RESOLVED: Resolved Alert ID {alert_id} ({alert.alert_type})",
            ip_address=request.remote_addr or '127.0.0.1'
        )
        audit.save()
        flash(f"Alert ID {alert_id} marked as resolved.", "success")
    except Exception as e:
        current_app.logger.error(f"Error resolving alert: {str(e)}")
        flash("Failed to resolve alert.", "danger")
        
    return redirect(url_for('telemetry.threat_analytics'))


@telemetry_bp.route('/api/telemetry/charts', methods=['GET'])
@login_required
@permission_required('view_analytics')
def api_telemetry_charts():
    """Retrieve telemetry metrics for loading Chart.js visual structures."""
    try:
        # 1. Role Distribution
        role_data = {}
        for u in User.get_all():
            if u.role:
                role_data[u.role] = role_data.get(u.role, 0) + 1
        
        # 2. Risk Level Distribution
        risk_data = {'Low': 0, 'Medium': 0, 'High': 0}
        for rs in RiskScore.get_all():
            if rs.risk_level in risk_data:
                risk_data[rs.risk_level] += 1
            else:
                risk_data[rs.risk_level] = 1

        # 3. Security Actions Trend
        # Group top actions
        action_counts = {}
        for log in AuditLog.get_all():
            if log.action:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
        sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:7]
        action_data = {k: v for k, v in sorted_actions}

        # 4. Behavioral Alert Categories
        alert_data = {}
        for alert in BehaviorAlert.get_all():
            if alert.alert_type:
                alert_data[alert.alert_type] = alert_data.get(alert.alert_type, 0) + 1

        return jsonify({
            'role_distribution': role_data,
            'risk_distribution': risk_data,
            'action_distribution': action_data,
            'alert_distribution': alert_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error serving telemetry API: {str(e)}")
        return jsonify({'error': 'Failed to compile telemetry metrics'}), 500
