import logging
import random
import string
try:
    import colorama

    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, WebDriverException
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
except Exception:
    logging.error(
        'Could not import all required modules. '\
        'Please run the following command again:\n\n'\
        '\tpipenv install\n')
    exit()

import sniper.constants as const


def scroll_to(driver, element):
    driver.execute_script(
        'arguments[0].scrollIntoView({block: "center"})', element)


def get_product_page(driver, locale, gpu, anticache=False):
    anticache_key = ''.join(random.choice(string.ascii_lowercase)
                            for i in range(5))
    anticache_value = random.randint(0, 9999)
    anticache_query = f'?{anticache_key}={anticache_value}'
    full_url = f"https://www.nvidia.com/{locale}{gpu['url']}"
    if anticache:
        full_url += anticache_query
    try:
        driver.get(full_url)
        return True
    except (TimeoutException, WebDriverException):
        return False


def check_availability(driver, timeout):
    try:
        add_to_basket_clickable = EC.element_to_be_clickable(
            (By.CSS_SELECTOR, const.ADD_TO_BASKET_SELECTOR))
        WebDriverWait(driver, timeout).until(add_to_basket_clickable)
        return True
    except TimeoutException:
        return False


def add_to_basket(driver, timeout):
    try:
        add_to_basket_btn = driver.find_element(
            By.CSS_SELECTOR, const.ADD_TO_BASKET_SELECTOR)
        scroll_to(driver, add_to_basket_btn)
        add_to_basket_btn.click()
        return True
    except (NoSuchElementException, ElementClickInterceptedException):
        return False


def to_checkout(driver, timeout, locale, notification_queue):
    try:
        try:
            cart_btn = driver.find_element(
                By.CLASS_NAME, const.CART_ICON_CLASS).click()
            if cart_btn is not None:
                cart_btn.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            pass

        checkout_clickable = EC.element_to_be_clickable(
            (By.CSS_SELECTOR, const.CHECKOUT_BUTTON_SELECTOR))
        WebDriverWait(driver, timeout).until(checkout_clickable)
        checkout_btn = driver.find_element(
            By.CSS_SELECTOR, const.CHECKOUT_BUTTON_SELECTOR)
        checkout_btn.click()

        logging.error('Trying to click pre checkout reCAPTCHA!')
        # Click CAPTCHA checkbox once and continue
        try:
            click_recaptcha(driver, timeout)
        except NoSuchElementException:
            pass

        while True:
            # Wait until checkout page is reached, in the worst case manual intervention is required
            try:
                WebDriverWait(driver, timeout).until(
                    EC.url_contains(const.STORE_HOST))
                return True
            except TimeoutException:
                logging.error(
                    'Could not reach checkout page, manual intervention might be required!')
                driver.save_screenshot(const.SCREENSHOT_FILE)
                notification_queue.put('captcha-fail')

    except (TimeoutException, NoSuchElementException):
        return False


def fill_out_form(driver, timeout, customer):
    driver.find_element(By.ID, 'billingName1').send_keys(
        customer['billing']['first-name'])
    driver.find_element(By.ID, 'billingName2').send_keys(
        customer['billing']['last-name'])

    driver.find_element(By.ID, 'billingAddress1').send_keys(
        customer['billing']['address-line-1'])
    driver.find_element(By.ID, 'billingAddress2').send_keys(
        customer['billing']['address-line-2'])

    try:
        driver.find_element(By.ID, 'billingState')
        state_select = Select(driver.find_element_by_id('billingState'))
        state_select.select_by_value(customer['billing']['state'])
    except NoSuchElementException:
        pass

    try:
        driver.find_element(By.ID, 'billingCountry')
        country_select = Select(driver.find_element_by_id('billingCountry'))
        country_select.select_by_value(customer['billing']['country'])
    except NoSuchElementException:
        pass

    driver.find_element(By.ID, 'billingCity').send_keys(
        customer['billing']['city'])
    driver.find_element(By.ID, 'billingPostalCode').send_keys(
        customer['billing']['post-code'])

    driver.find_element(By.ID, 'billingPhoneNumber').send_keys(
        customer['billing']['phone'])
    driver.find_element(By.ID, 'email').send_keys(
        customer['billing']['email'])
    driver.find_element(By.ID, 'verEmail').send_keys(
        customer['billing']['email'])

    if 'shipping' in customer:
        try:
            shipping_speed = customer['shipping']['speed']
            driver.find_element(By.ID, shipping_speed).click()
        except Exception:
            logging.warning(f'Could not find shipping speed {shipping_speed}')
            if 'backup-speed' in customer['shipping']:
                if customer['shipping']['backup-speed']:
                    logging.info('Continuing with default speed')
                else:
                    logging.info('User opted to stop if shipping speed not found.')
                    exit()
            else:
                logging.warning(
                    'data/customer.json missing "backup-speed" option under "shipping", '\
                    'continuing with default speed')
                   

        shipping_expanded = False
        while not shipping_expanded:
            try:
                driver.find_element(By.ID, 'shippingName1').send_keys(
                    customer['shipping']['first-name'])
                shipping_expanded = True
            except ElementNotInteractableException:
                expand_shipping_button = driver.find_element(
                    By.ID, 'shippingDifferentThanBilling')
                scroll_to(driver, expand_shipping_button)
                expand_shipping_button.click()
                shipping_visible = EC.visibility_of_element_located(
                    (By.ID, 'shippingName1'))
                WebDriverWait(driver, timeout).until(shipping_visible)

        driver.find_element(By.ID, 'shippingName2').send_keys(
            customer['shipping']['last-name'])

        driver.find_element(By.ID, 'shippingAddress1').send_keys(
            customer['shipping']['address-line-1'])
        driver.find_element(By.ID, 'shippingAddress2').send_keys(
            customer['shipping']['address-line-2'])

        try:
            driver.find_element(By.ID, 'shippingState')
            state_select = Select(driver.find_element_by_id('shippingState'))
            state_select.select_by_value(customer['shipping']['state'])
        except NoSuchElementException:
            pass

        try:
            driver.find_element(By.ID, 'shippingCountry')
            country_select = Select(
                driver.find_element_by_id('shippingCountry'))
            country_select.select_by_value(customer['shipping']['country'])
        except NoSuchElementException:
            pass

        driver.find_element(By.ID, 'shippingCity').send_keys(
            customer['shipping']['city'])
        driver.find_element(By.ID, 'shippingPostalCode').send_keys(
            customer['shipping']['post-code'])

        driver.find_element(By.ID, 'shippingPhoneNumber').send_keys(
            customer['shipping']['phone'])

    driver.find_element(By.ID, 'ccNum').send_keys(
        customer['credit']['card'])

    month_select = Select(driver.find_element_by_id('expirationDateMonth'))
    month_select.select_by_value(customer['credit']['expiration']['month'].lstrip('0'))

    year_select = Select(driver.find_element_by_id('expirationDateYear'))
    year_select.select_by_value(customer['credit']['expiration']['year'])

    driver.find_element(By.ID, 'cardSecurityCode').send_keys(
        customer['credit']['code'])


def skip_address_check(driver, customer):
    if customer['billing']['force']:
        driver.find_element(By.ID, 'billingAddressOptionRow1').click()
    else:
        driver.find_element(By.ID, 'billingAddressOptionRow2').click()
    if customer['shipping']['force']:
        driver.find_element(By.ID, 'shippingAddressOptionRow1').click()
    else:
        driver.find_element(By.ID, 'shippingAddressOptionRow2').click()
    driver.find_element(By.ID, 'selectionButton').click()


def click_recaptcha(driver, timeout):
    recaptcha_frame = driver.find_element(
        By.CSS_SELECTOR, const.RECAPTCHA_FRAME_SELECTOR)
    scroll_to(driver, recaptcha_frame)
    recaptcha_ready = EC.frame_to_be_available_and_switch_to_it(
        (By.CSS_SELECTOR, const.RECAPTCHA_FRAME_SELECTOR))
    WebDriverWait(driver, timeout).until(recaptcha_ready)
    checkbox_ready = EC.element_to_be_clickable(
        (By.XPATH, const.RECAPTCHA_BOX_XPATH))
    WebDriverWait(driver, timeout).until(checkbox_ready).click()
    driver.switch_to.default_content()


def submit_order(driver, timeout):
    try:
        submit_clickable = EC.element_to_be_clickable(
            (By.CSS_SELECTOR, const.SUBMIT_BUTTON_SELECTOR))
        WebDriverWait(driver, timeout).until(submit_clickable)
        driver.find_element(
            By.CSS_SELECTOR, const.SUBMIT_BUTTON_SELECTOR).click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        return False


def checkout_guest(driver, timeout, customer, auto_submit=False):
    proceeded_to_form = False
    logging.info('Checking out as guest...')
    while not proceeded_to_form:
        try:
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, const.CHECKOUT_AS_GUEST_ID)))
            guest_checkout_btn = driver.find_element(
                By.ID, const.CHECKOUT_AS_GUEST_ID)
            scroll_to(driver, guest_checkout_btn)
            guest_checkout_btn.click()
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, 'billingName1')))
            proceeded_to_form = True
        except TimeoutException:
            logging.info(
                'Timed out waiting for checkout button to load, trying again...')
            driver.get('https://store.nvidia.com/store/nvidia/cart')

    fill_out_form(driver, timeout, customer)
    driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
    driver.find_element(By.CSS_SELECTOR, const.SUBMIT_BUTTON_SELECTOR).click()

    try:
        driver.find_element(By.CLASS_NAME, 'dr_error')
        skip_address_check(driver, customer)
    except NoSuchElementException:
        pass


def checkout_paypal(driver, timeout):
    proceeded_to_paypal = False
    logging.info('Checking out using PayPal Express...')
    while not proceeded_to_paypal:
        try:
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, const.PAYPAL_BUTTON_ID)))
            driver.find_element(By.ID, const.PAYPAL_BUTTON_ID).click()
            proceeded_to_paypal = True
        except TimeoutException:
            logging.info(
                'Timed out waiting for PayPal button to load, trying again...')
            driver.get('https://store.nvidia.com/store/nvidia/cart')
