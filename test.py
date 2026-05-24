def sync_lpus_loyalty_program_data(lpus_loyalty_program_data: list[LpuLoyaltyProgramAPIData]) -> None:
    """
    Синхронизировать данные о программе лояльности в нескольких ЛПУ.

    :param lpus_loyalty_program_data: Данные программы лояльности в нескольких ЛПУ.
    """
    # Агрегируем данные
    lpus_loyalty_data_to_create = []
    lpus_ids_loyalty_data_to_delete = []
    for lpu_loyalty_program_data in lpus_loyalty_program_data:
        if lpu_loyalty_program_data['is_enabled']:
            lpus_loyalty_data_to_create.append(lpu_loyalty_program_data)
        else:
            lpus_ids_loyalty_data_to_delete.append(lpu_loyalty_program_data['lpu_id'])

    lpu_loyalty_infos_to_create = (
        LpuLoyaltyInfo(
            lpu_id=lpu_loyalty_info['lpu_id'],
            max_payment_percent=lpu_loyalty_info['max_payment_percent'],
            welcome_bonus_amount=lpu_loyalty_info['welcome_bonus_amount'],
        )
        for lpu_loyalty_info in lpus_loyalty_data_to_create
    )
    lpu_loyalty_level_infos_to_create = (
        LpuLoyaltyLevelInfo(
            lpu_id=lpu_loyalty_info['lpu_id'],
            level=lpu_loyalty_level_info['level'],
            need_spend=lpu_loyalty_level_info['need_spend'],
            percent_amount=lpu_loyalty_level_info['percent_amount'],
        )
        for lpu_loyalty_info in lpus_loyalty_data_to_create
        for lpu_loyalty_level_info in lpu_loyalty_info['levels']
    )
    # Собираем Query, чтобы удалить неактуальные уровни программы лояльности
    lpu_loyalty_level_infos_to_delete = ALWAYS_FALSE_Q
    for lpu_loyalty_info in lpus_loyalty_data_to_create:
        lpu_loyalty_info_levels = [
            lpu_loyalty_level_info['level']
            for lpu_loyalty_level_info in lpu_loyalty_info['levels']
        ]
        lpu_loyalty_level_infos_to_delete |= (
            Q(lpu_id=lpu_loyalty_info['lpu_id'])
            & ~Q(level__in=lpu_loyalty_info_levels)
        )

    with transaction.atomic():
        # Удаляем данные по отключённым программам
        LpuLoyaltyInfo.objects.filter(lpu_id__in=lpus_ids_loyalty_data_to_delete).delete()
        LpuLoyaltyLevelInfo.objects.filter(lpu_id__in=lpus_ids_loyalty_data_to_delete).delete()

        # Удаляем данные по неактуальным уровням
        LpuLoyaltyLevelInfo.objects.filter(lpu_loyalty_level_infos_to_delete).delete()

        # Обновляем данные по включённым программам
        LpuLoyaltyInfo.objects.bulk_create(
            lpu_loyalty_infos_to_create,
            batch_size=100,
            update_conflicts=True,
            update_fields=[
                'max_payment_percent',
                'welcome_bonus_amount',
            ],
            unique_fields=['lpu_id'],
        )
        LpuLoyaltyLevelInfo.objects.bulk_create(
            lpu_loyalty_level_infos_to_create,
            batch_size=100,
            update_conflicts=True,
            update_fields=[
                'need_spend',
                'percent_amount',
            ],
            unique_fields=['lpu_id', 'level'],
        )