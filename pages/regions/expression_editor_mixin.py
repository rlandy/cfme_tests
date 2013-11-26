# -*- coding: utf-8 -*-
from pages.base import Base
from selenium.webdriver.common.by import By
import time


class ExpressionEditorMixin(Base):
    _edit_chosen_type_locator = (By.CSS_SELECTOR, "select#chosen_typ")
    _edit_chosen_field_locator = (By.CSS_SELECTOR, "select#chosen_field")
    _edit_chosen_count_locator = (By.CSS_SELECTOR, "select#chosen_count")
    _edit_chosen_tag_locator = (By.CSS_SELECTOR, "select#chosen_tag")
    _edit_chosen_key_locator = (By.CSS_SELECTOR, "select#chosen_key")
    _edit_chosen_skey_locator = (By.CSS_SELECTOR, "select#chosen_skey")
    _edit_chosen_check_locator = (By.CSS_SELECTOR, "select#chosen_check")
    _edit_chosen_cfield_locator = (By.CSS_SELECTOR, "select#chosen_cfield")
    _edit_chosen_regkey_locator = (By.CSS_SELECTOR, "input#chosen_regkey")
    _edit_chosen_regval_locator = (By.CSS_SELECTOR, "input#chosen_regval")
    _edit_chosen_value_locator = (By.CSS_SELECTOR, "#chosen_value")
    _edit_textarea_chosen_value_locator = (By.CSS_SELECTOR, "textarea#chosen_value")
    _commit_expression_button = (By.CSS_SELECTOR,
        "ul#searchtoolbar > li > a > img[alt='Commit expression element changes']")
    _discard_expression_button = (By.CSS_SELECTOR,
        "ul#searchtoolbar > li > a > img[alt='Discard expression element changes']")
    _selected_expression_locator = (By.CSS_SELECTOR,
        "a[style*='yellow'][style*='background-color']")

    _remove_selected_expression_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='Remove this expression element']")
    _undo_change_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='Undo the previous change']")
    _redo_change_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='Redo the next change']")
    _AND_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='AND with a new expression element']")
    _OR_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='OR with a new expression element']")
    _NOT_locator = (By.CSS_SELECTOR,
        "span:not([style*='none']) > li > a[title='Wrap this expression element with a NOT']")

    _expression_link_locator = (By.CSS_SELECTOR, "a[id*='exp_']")

    @property
    def discard_expression_button(self):
        return self.selenium.find_element(*self._discard_expression_button)

    @property
    def commit_expression_button(self):
        return self.selenium.find_element(*self._commit_expression_button)

    @property
    def selected_expression(self):
        return self.selenium.find_element(*self._selected_expression_locator)

    @property
    def all_expressions(self):
        return self.selenium.find_elements(*self._expression_link_locator)

    @property
    def expressions_count(self):
        return len(self.all_expressions)

    @property
    def is_selected_expression(self):
        return self.is_element_present(*self._selected_expression_locator)

    @property
    def first_expression(self):
        return self.all_expressions[0]

    @property
    def remove_selected_expression_button(self):
        return self.selenium.find_element(*self._remove_selected_expression_locator)

    @property
    def undo_button(self):
        return self.selenium.find_element(*self._undo_change_locator)

    @property
    def redo_button(self):
        return self.selenium.find_element(*self._redo_change_locator)

    @property
    def AND_button(self):
        return self.selenium.find_element(*self._AND_locator)

    @property
    def OR_button(self):
        return self.selenium.find_element(*self._OR_locator)

    @property
    def NOT_button(self):
        return self.selenium.find_element(*self._NOT_locator)

    def undo_change(self):
        """ Clicks on Undo change button.

        """
        self.undo_button.click()
        self._wait_for_results_refresh()
        return self

    def redo_change(self):
        """ Clicks on Redochange button.

        """
        self.redo_button.click()
        self._wait_for_results_refresh()
        return self

    def AND_expression(self):
        """ Clicks on AND button.

        """
        self.AND_button.click()
        self._wait_for_results_refresh()
        return self

    def OR_expression(self):
        """ Clicks on OR button.

        """
        self.OR_button.click()
        self._wait_for_results_refresh()
        return self

    def NOT_expression(self):
        """ Clicks on NOT button.

        """
        self.NOT_button.click()
        self._wait_for_results_refresh()
        return self

    def select_first_expression(self):
        """ Selects first available expression.

        """
        if self.is_selected_expression and self.selected_expression.text.strip() == "???":
            if self.expressions_count > 1:  # To check the case that the ??? is only one
                raise Exception("When editing opened, you cannot change to another expression")
        self.first_expression.click()
        self._wait_for_results_refresh()

    def select_expression_by_text(self, text):
        """ Looks for the expression which contains specific text

        @param text: Text to look for
        """
        # All expressions have id like exp_*
        locator = (By.XPATH, "//a[contains(@id, 'exp_') and contains(text(), '%s')]" % text)
        self._wait_for_visible_element(*locator, visible_timeout=10)
        expression = self.selenium.find_element(*locator)
        exp_id = expression.get_attribute("id")
        expression.click()
        # Selected (highlighted) expressions have style with background-color:yellow
        # However, sometimes there is a space between : and y and sometimes not
        # Therefore this ugly thing
        self._wait_for_visible_element(By.CSS_SELECTOR,
                "a[id='%s'][style*='yellow'][style*='background-color']" % (exp_id),
                visible_timeout=10)

    def delete_selected_expression(self):
        """ Delete selected expression.

        If the selected expression is not ???, which means it cannot be deleted,
        it will be deleted.

        @return: True if it wasn't ???, False if it was.
        """
        assert self.is_selected_expression, "Element must be selected prior to deleting"
        if self.selected_expression.text.strip() != "???":
            self._wait_for_visible_element(*self._remove_selected_expression_locator,
                                           visible_timeout=10)
            self.remove_selected_expression_button.click()
            self._wait_for_results_refresh()
            return True
        return False

    def delete_first_expression(self):
        """ Select first expression and the delete it.

        """
        self.select_first_expression()
        return self.delete_selected_expression()

    def delete_all_expressions(self):
        """ Iterates with deleting the first expression until ??? is present.

        """
        while self.delete_first_expression():
            continue

    def discard_expression(self):
        """ Discard changes made on an expression.

        Requires to have any expression open.
        """
        assert self.is_selected_expression, "You must select an expression!"
        # Sleeping to prevent some glitches like not saving the expression, etc.
        time.sleep(1)
        self.discard_expression_button.click()
        time.sleep(1)
        self._wait_for_results_refresh()
        return self

    def commit_expression(self):
        """ Commit changes made on an expression.

        Requires to have any expression open.
        """
        assert self.is_selected_expression, "You must select an expression!"
        # Sleeping to prevent some glitches like not discarding the expression, etc.
        time.sleep(1)
        self.commit_expression_button.click()
        time.sleep(1)
        self._wait_for_results_refresh()
        return self

    def fill_expression_field(self, chosen_field, chosen_key, chosen_value):
        """ Fill expression with the data. Field type

        Handles difference between the select and text inputs on chosen_value.
        """
        chosen_type = "Field"
        # chosen_type
        self._wait_for_visible_element(*self._edit_chosen_type_locator)
        self.select_dropdown(chosen_type, *self._edit_chosen_type_locator)

        # chosen_field
        self._wait_for_visible_element(*self._edit_chosen_field_locator)
        self.select_dropdown(chosen_field, *self._edit_chosen_field_locator)

        # chosen_key
        self._wait_for_visible_element(*self._edit_chosen_key_locator)
        self.select_dropdown(chosen_key, *self._edit_chosen_key_locator)

        if chosen_key.lower().strip() == "ruby":
            self._wait_for_visible_element(*self._edit_textarea_chosen_value_locator,
                                           visible_timeout=15)
        else:
            time.sleep(5)

        # chosen_value
        self._wait_for_visible_element(*self._edit_chosen_value_locator)
        e = self.selenium.find_element(*self._edit_chosen_value_locator)
        if e.tag_name == "select":
            self.select_dropdown(chosen_value, *self._edit_chosen_value_locator)
        elif e.tag_name in ["input", "textarea"]:
            self.fill_field_element(chosen_value, e)
        else:
            raise Exception("Unknown tag name %s, locals dump (%s)" % (e.tag_name, locals()))

    def fill_expression_count(self, chosen_count, chosen_key, chosen_value):
        """ Fill expression with the data. Count type

        Handles difference between the select and text inputs on chosen_value.
        """
        chosen_type = "Count of"
        # chosen_type
        self._wait_for_visible_element(*self._edit_chosen_type_locator)
        self.select_dropdown(chosen_type, *self._edit_chosen_type_locator)

        # chosen_count
        self._wait_for_visible_element(*self._edit_chosen_count_locator)
        self.select_dropdown(chosen_count, *self._edit_chosen_count_locator)

        # chosen_key
        self._wait_for_visible_element(*self._edit_chosen_key_locator)
        self.select_dropdown(chosen_key, *self._edit_chosen_key_locator)

        # chosen_value
        self._wait_for_visible_element(*self._edit_chosen_value_locator)
        self.fill_field_by_locator(chosen_value, *self._edit_chosen_value_locator)

    def fill_expression_tag(self, chosen_tag, chosen_value):
        """ Fill expression with the data. Tag type

        """
        chosen_type = "Tag"
        # chosen_type
        self._wait_for_visible_element(*self._edit_chosen_type_locator)
        self.select_dropdown(chosen_type, *self._edit_chosen_type_locator)

        # chosen_count
        self._wait_for_visible_element(*self._edit_chosen_tag_locator)
        self.select_dropdown(chosen_tag, *self._edit_chosen_tag_locator)

        # chosen_value
        self._wait_for_visible_element(*self._edit_chosen_value_locator)
        self.select_dropdown(chosen_value, *self._edit_chosen_value_locator)

    def fill_expression_find(self,
                             chosen_field,
                             chosen_skey,
                             chosen_check,
                             chosen_cfield,
                             chosen_value=None):
        """ Fill expression with the data. Find type

        """
        chosen_type = "Find"
        # chosen_type
        self._wait_for_visible_element(*self._edit_chosen_type_locator)
        self.select_dropdown(chosen_type, *self._edit_chosen_type_locator)

        # chosen_field
        self._wait_for_visible_element(*self._edit_chosen_field_locator)
        self.select_dropdown(chosen_field, *self._edit_chosen_field_locator)

        # chosen_skey
        self._wait_for_visible_element(*self._edit_chosen_skey_locator)
        self.select_dropdown(chosen_skey, *self._edit_chosen_skey_locator)

        # chosen_value
        if chosen_value:
            self._wait_for_visible_element(*self._edit_chosen_value_locator)
            self.fill_field_by_locator(chosen_value, *self._edit_chosen_value_locator)

        # chosen_check
        self._wait_for_visible_element(*self._edit_chosen_check_locator)
        self.select_dropdown(chosen_check, *self._edit_chosen_check_locator)

        # chosen_cfield
        self._wait_for_visible_element(*self._edit_chosen_cfield_locator)
        self.select_dropdown(chosen_cfield, *self._edit_chosen_cfield_locator)

    def fill_expression_registry(self, chosen_regkey, chosen_regval, chosen_key, chosen_value):
        """ Fill expression with the data. Registry type

        """
        chosen_type = "Registry"
        # chosen_type
        self._wait_for_visible_element(*self._edit_chosen_type_locator)
        self.select_dropdown(chosen_type, *self._edit_chosen_type_locator)

        # chosen_regkey
        self._wait_for_visible_element(*self._edit_chosen_regkey_locator)
        self.fill_field_by_locator(chosen_regkey, *self._edit_chosen_regkey_locator)

        # chosen_regval
        self._wait_for_visible_element(*self._edit_chosen_regval_locator)
        self.fill_field_by_locator(chosen_regval, *self._edit_chosen_regval_locator)

        # chosen_key
        self._wait_for_visible_element(*self._edit_chosen_key_locator)
        self.select_dropdown(chosen_key, *self._edit_chosen_key_locator)

        # chosen_value
        self._wait_for_visible_element(*self._edit_chosen_value_locator)
        self.select_dropdown(chosen_value, *self._edit_chosen_value_locator)