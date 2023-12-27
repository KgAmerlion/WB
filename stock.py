
# получение отчета о продажах и заказах по нажатию кнопки

@router.message(F.text == "Отчет")
async def sales_shop_name(message: Message, state: FSMContext):
    await message.answer(text='Пожалуйста, введите название магазина для получения отчета')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(Form.name)


@router.message(StateFilter(Form.name), F.text)
async def analyse_shop(message: Message, state: FSMContext):
    # Cохраняем название магазина для удаления
    await state.update_data(name=message.text)
    # await message.answer(text='Спасибо!\n\n Получаем отчет')

    #
    shop_to_analyse = await state.get_data()

    db = sq.connect('my_bd.sql')
    cur = db.cursor()
    cur.execute(
        "SELECT wb_token FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
        shop_to_analyse['name'], message.from_user.id))

    info = cur.fetchall()
    api = info[0][0]
    cur.close()
    db.close()

    # Завершаем машину состояний
    await state.clear()

    # выгрузка
    headers["Authorization"] = api
    init = 'https://statistics-api.wildberries.ru/api/v1/supplier/'

    date_from = datetime.today()

    results = {i: f'{init}{i}?dateFrom={date_from}&flag=1' for i in ['sales', 'orders']}
    sales = pd.DataFrame(requests.get(results['sales'], headers=headers).json())  # продажи
    orders = pd.DataFrame(requests.get(results['orders'], headers=headers).json())  # заказы

    sales['date_column'] = pd.to_datetime(sales['date']).dt.date
    orders['date_column'] = pd.to_datetime(orders['date']).dt.date

    ttl_sum_sales = sum(sales['priceWithDisc'])
    ttl_sum_orders = sum(orders['priceWithDisc'])

    await message.answer(f'Выкупили: {ttl_sum_sales}\n'
                         f'Заказали: {ttl_sum_orders}')

# async def notif(bot: Bot, chat_id: int):
#     await bot.send_message(chat_id, f'привет')
#
#

#     apscheduler.add_job(notif, trigger='interval', minutes=2,
#                          kwargs={'bot': bot, 'chat_id': user})
# @router.message(F.text == 'Рассылка')
# async def subs_name_shop(message: Message, state: FSMContext):
#     await message.answer(text='Пожалуйста, введите название магазина')
#     # Устанавливаем состояние ожидания ввода имени
#     await state.set_state(Subsc.name)
#
#
# async def get_api(shop_to_subscribe, bot, chat_id, apscheduler):
#     db = sq.connect('my_bd.sql')
#     cur = db.cursor()
#     cur.execute(
#         "SELECT wb_token FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
#             shop_to_subscribe['name'], chat_id))
#     info = cur.fetchall()
#     cur.close()
#     db.close()
#     # выгрузка
#     if len(info) != 0:
#         api = info[0][0]
#         headers["Authorization"] = api
#         init = 'https://statistics-api.wildberries.ru/api/v1/supplier/'
#
#         date_from = datetime.today()
#
#         results = {i: f'{init}{i}?dateFrom={date_from}&flag=1' for i in ['sales', 'orders']}
#         sales = pd.DataFrame(requests.get(results['sales'], headers=headers).json())  # продажи
#         orders = pd.DataFrame(requests.get(results['orders'], headers=headers).json())  # заказы
#
#         sales['date_column'] = pd.to_datetime(sales['date']).dt.date
#         orders['date_column'] = pd.to_datetime(orders['date']).dt.date
#
#         ttl_sum_sales = sum(sales['priceWithDisc'])
#         ttl_sum_orders = sum(orders['priceWithDisc'])
#         await bot.send_message(chat_id, f"Магазин: {shop_to_subscribe['name']}\n"
#                                         f"Выкупили: {ttl_sum_sales}\n"
#                                         f"Заказали: {ttl_sum_orders}")
#     else:
#         await bot.send_message(chat_id, f'Такого магазина нет в списке')
#         apscheduler.remove_job('subscription')
#
#
# @router.message(StateFilter(Subsc.name), F.text)
# async def subscribe_shop(message: Message, bot: Bot, apscheduler: AsyncIOScheduler, state: FSMContext):
#     # Cохраняем название магазина
#     await state.update_data(name=message.text)
#     shop_to_subscribe = await state.get_data()
#     user = message.from_user.id
#     # Завершаем машину состояний
#     await state.clear()
#     db = sq.connect('my_bd.sql')
#     cur = db.cursor()
#     cur.execute(
#         "SELECT wb_token FROM profiles WHERE name == '%s' AND user_id == '%i'" % (
#             shop_to_subscribe['name'], user))
#     info = cur.fetchall()
#     cur.close()
#     db.close()
#     # выгрузка
#     if len(info) != 0:
#         await message.answer(f'Рассылка включена. Отчет будет присылаться каждые 3 часа')
#         apscheduler.add_job(get_api,
#                             trigger='interval',
#                             seconds=30,
#                             kwargs={'shop_to_subscribe': shop_to_subscribe, 'bot': bot, 'chat_id': user,
#                                     'apscheduler': apscheduler},
#                             id=f'subscription_{i}')
#
#     else:
#         await message.answer(f'Такого магазина нет в списке')





