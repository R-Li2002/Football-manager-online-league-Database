"""
Fly.io 使用量监控脚本
用于跟踪资源使用情况，防止超出免费额度
"""

import requests
import json
from datetime import datetime
from pathlib import Path

# 配置部分
FLY_API_TOKEN = "your_fly_api_token"  # 替换为您的 Fly.io API Token
ORG_SLUG = "your_org_slug"  # 替换为您的组织名称
ALERT_EMAIL = "your_email@example.com"  # 替换为您的邮箱

# 告警阈值
THRESHOLDS = {
    "vm_cost_usd": 5.0,      # VM 费用超过$5 告警
    "volume_gb": 2.5,        # 存储超过 2.5GB 告警
    "bandwidth_gb": 150,     # 流量超过 150GB 告警
    "total_cost_usd": 8.0    # 总费用超过$8 告警
}

def get_fly_api_headers():
    """获取 Fly.io API 请求头"""
    return {
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json"
    }

def get_organization_id():
    """获取组织 ID"""
    url = "https://api.fly.io/api/v1/organizations"
    response = requests.get(url, headers=get_fly_api_headers())
    
    if response.status_code == 200:
        orgs = response.json()["data"]["organizations"]
        for org in orgs:
            if org["slug"] == ORG_SLUG:
                return org["id"]
    return None

def get_current_usage():
    """获取当前使用量"""
    org_id = get_organization_id()
    if not org_id:
        print("❌ 无法获取组织 ID")
        return None
    
    # 获取应用列表
    apps_url = f"https://api.fly.io/api/v1/organizations/{org_id}/apps"
    response = requests.get(apps_url, headers=get_fly_api_headers())
    
    if response.status_code != 200:
        print(f"❌ 获取应用列表失败：{response.status_code}")
        return None
    
    apps = response.json()["data"]["organizations"]["nodes"][0]["apps"]["nodes"]
    
    usage_info = {
        "timestamp": datetime.now().isoformat(),
        "apps": [],
        "total_vms": 0,
        "total_volume_gb": 0,
        "estimated_cost": 0
    }
    
    for app in apps:
        app_name = app["name"]
        if app_name != "heigo-league-db":
            continue
        
        app_info = {
            "name": app_name,
            "status": app["status"],
            "vm_count": 0,
            "volume_gb": 0
        }
        
        # 获取 VM 信息
        machines_url = f"https://api.fly.io/api/v1/apps/{app_name}/machines"
        machines_response = requests.get(machines_url, headers=get_fly_api_headers())
        
        if machines_response.status_code == 200:
            machines = machines_response.json()
            app_info["vm_count"] = len(machines)
            usage_info["total_vms"] += len(machines)
        
        # 获取 Volume 信息
        volumes_url = f"https://api.fly.io/api/v1/apps/{app_name}/volumes"
        volumes_response = requests.get(volumes_url, headers=get_fly_api_headers())
        
        if volumes_response.status_code == 200:
            volumes = volumes_response.json()["data"]["app"]["volumes"]["nodes"]
            total_gb = sum(v["sizeGb"] for v in volumes)
            app_info["volume_gb"] = total_gb
            usage_info["total_volume_gb"] += total_gb
        
        usage_info["apps"].append(app_info)
    
    # 估算成本
    vm_cost = usage_info["total_vms"] * 2.02  # shared-cpu-1x 256MB
    volume_cost = usage_info["total_volume_gb"] * 0.15
    ipv4_cost = 2.00  # 假设使用 1 个 IPv4
    
    usage_info["estimated_cost"] = vm_cost + volume_cost + ipv4_cost
    usage_info["cost_breakdown"] = {
        "vm_cost": vm_cost,
        "volume_cost": volume_cost,
        "ipv4_cost": ipv4_cost
    }
    
    return usage_info

def check_thresholds(usage_info):
    """检查是否超过阈值"""
    alerts = []
    
    cost_breakdown = usage_info.get("cost_breakdown", {})
    
    if cost_breakdown.get("vm_cost", 0) > THRESHOLDS["vm_cost_usd"]:
        alerts.append(f"⚠️ VM 费用警告：${cost_breakdown['vm_cost']:.2f} (阈值：${THRESHOLDS['vm_cost_usd']})")
    
    if usage_info["total_volume_gb"] > THRESHOLDS["volume_gb"]:
        alerts.append(f"⚠️ 存储警告：{usage_info['total_volume_gb']:.2f}GB (阈值：{THRESHOLDS['volume_gb']}GB)")
    
    if usage_info["estimated_cost"] > THRESHOLDS["total_cost_usd"]:
        alerts.append(f"⚠️ 总费用警告：${usage_info['estimated_cost']:.2f} (阈值：${THRESHOLDS['total_cost_usd']})")
    
    return alerts

def send_alert(message):
    """发送告警（这里只是打印，可以扩展为邮件/短信）"""
    print("\n" + "="*50)
    print("🚨 FLY.IO 使用量告警")
    print("="*50)
    print(message)
    print("="*50 + "\n")
    
    # TODO: 实现邮件发送
    # import smtplib
    # from email.mime.text import MIMEText
    # ...

def save_usage_log(usage_info):
    """保存使用量日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "fly_usage.log"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(usage_info, ensure_ascii=False) + "\n")

def generate_report():
    """生成使用量报告"""
    print("\n" + "="*50)
    print("📊 FLY.IO 使用量报告")
    print("="*50)
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*50)
    
    usage_info = get_current_usage()
    
    if not usage_info:
        print("❌ 无法获取使用量信息")
        return
    
    print(f"运行中的 VM 数量：{usage_info['total_vms']}")
    print(f"存储使用量：{usage_info['total_volume_gb']:.2f} GB")
    print("-"*50)
    
    cost = usage_info.get("cost_breakdown", {})
    print("成本估算:")
    print(f"  - VM 费用：${cost.get('vm_cost', 0):.2f}/月")
    print(f"  - 存储费用：${cost.get('volume_cost', 0):.2f}/月")
    print(f"  - IPv4 费用：${cost.get('ipv4_cost', 0):.2f}/月")
    print(f"  - 总计：${usage_info['estimated_cost']:.2f}/月")
    print("-"*50)
    
    # 检查阈值
    alerts = check_thresholds(usage_info)
    
    if alerts:
        for alert in alerts:
            print(alert)
        send_alert("\n".join(alerts))
    else:
        print("✅ 所有指标均在安全范围内")
    
    print("="*50 + "\n")
    
    # 保存日志
    save_usage_log(usage_info)

def main():
    """主函数"""
    try:
        generate_report()
    except Exception as e:
        print(f"❌ 监控脚本执行失败：{e}")

if __name__ == "__main__":
    main()
