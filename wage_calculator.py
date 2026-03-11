import math

from domain_types import SLOT_TYPE_7M, SLOT_TYPE_8M, SLOT_TYPE_FAKE, normalize_slot_type

def calculate_value_base(ca_value):
    """
    通用身价计算公式 (适用于初始CA、当前CA、PA)
    """
    if ca_value < 115:
        return 1
    else:
        return math.floor((ca_value - 95) / 10)

def calculate_initial_value(initial_ca):
    """
    一、初始身价计算逻辑
    """
    return calculate_value_base(initial_ca)

def calculate_current_value(current_ca):
    """
    二、当前身价计算逻辑
    """
    return calculate_value_base(current_ca)

def calculate_potential_value(pa):
    """
    三、潜力身价计算逻辑
    """
    return calculate_value_base(pa)

def calculate_final_value(initial_ca, current_ca, pa, age, growth_age_limit=24):
    """
    四、身价计算逻辑
    """
    initial_value = calculate_initial_value(initial_ca)
    current_value = calculate_current_value(current_ca)
    potential_value = calculate_potential_value(pa)
    
    if age > growth_age_limit:
        return current_value
    elif pa < 140:
        return initial_value
    else:
        return (current_value + potential_value) / 2

def calculate_initial_field(initial_ca, pa, age):
    """
    五、初始字段计算逻辑
    """
    initial_value = calculate_initial_value(initial_ca)
    potential_value = calculate_potential_value(pa)
    
    if age > 25:
        if initial_ca < 115:
            return 1
        else:
            return math.floor((initial_ca - 95) / 10)
    else:
        return (initial_value + potential_value) / 2

def calculate_slot_type(initial_field, pa, current_ca, age, growth_age_limit=24):
    """
    六、名额标签计算逻辑
    """
    if initial_field >= 8:
        return SLOT_TYPE_8M
    elif 7 <= initial_field < 8:
        return SLOT_TYPE_7M
    else:
        # 检查伪名资格
        condition1 = (age <= growth_age_limit) and (pa > 164)
        condition2 = (age > growth_age_limit) and (age < 26) and (current_ca > 164)
        if condition1 or condition2:
            return SLOT_TYPE_FAKE
        else:
            return ""

def calculate_coefficient(initial_field, current_ca, pa, age, position, slot_type, growth_age_limit=24):
    """
    七、系数计算逻辑
    """
    initial_value = calculate_initial_value(initial_field if initial_field >= 115 else 115)
    current_value = calculate_current_value(current_ca)
    slot_type = normalize_slot_type(slot_type)
    
    # 条件1: 门将且有名额标签
    if position == "GK" and slot_type != "":
        return 0.1
    
    # 条件2: 初始字段等于1
    if initial_field == 1:
        return 0.1
    
    # 条件3: (初始字段 + 当前身价)/2 等于1
    if (initial_field + current_value) / 2 == 1:
        return 0.1
    
    # 条件4: 8M
    if slot_type == SLOT_TYPE_8M:
        return 0.15
    
    # 条件5: 7M
    if slot_type == SLOT_TYPE_7M:
        return 0.13
    
    # 条件6: 伪名
    if slot_type == SLOT_TYPE_FAKE:
        return 0.11
    
    # 条件7: 按年龄和能力分段
    if age > growth_age_limit:
        temp_value = math.floor((current_ca - 95) / 10)
        if temp_value > 5:
            return 0.09
        else:
            return 0.07
    else:
        temp_value = math.floor((pa - 95) / 10)
        if temp_value > 5:
            return 0.09
        else:
            return 0.07

def calculate_wage(initial_ca, current_ca, pa, age, position, growth_age_limit=24):
    """
    八、工资计算逻辑 - 综合计算所有参数
    """
    # 计算各项值
    initial_value = calculate_initial_value(initial_ca)
    current_value = calculate_current_value(current_ca)
    potential_value = calculate_potential_value(pa)
    final_value = calculate_final_value(initial_ca, current_ca, pa, age, growth_age_limit)
    initial_field = calculate_initial_field(initial_ca, pa, age)
    slot_type = calculate_slot_type(initial_field, pa, current_ca, age, growth_age_limit)
    coefficient = calculate_coefficient(initial_field, current_ca, pa, age, position, slot_type, growth_age_limit)
    
    # 计算工资
    wage = round(final_value * coefficient, 3)
    
    return {
        "initial_value": initial_value,
        "current_value": current_value,
        "potential_value": potential_value,
        "final_value": final_value,
        "initial_field": initial_field,
        "slot_type": slot_type,
        "coefficient": coefficient,
        "wage": wage
    }
