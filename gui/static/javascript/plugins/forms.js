var grr = window.grr || {};

/**
 * Namespace for forms.
 */
grr.forms = {};


/**
 * An onchange function which updates the FormData container.
 *
 * @param {Object} element an input element.
 */
grr.forms.inputOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();

  json_store[jthis.attr('id')] = jthis.val();
  jthis.removeClass('unset');
};


/**
 * Change handler function for checkboxes which updates the FormData container.
 *
 * @param {Object} element an input element.
 */
grr.forms.checkboxOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();

  json_store[jthis.attr('id')] = jthis.is(':checked');
  jthis.removeClass('unset');
};


/**
 * Change handler function for select box which updates the FormData container.
 *
 * In this setup we want everything in the list box to be considered a value
 * not just the ones that are selected. Additionally this has be to called
 * manually, because the onchange only fires on selection, not addition to the
 * list.
 *
 * @param {Object} element an input element.
 */
grr.forms.selectOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();
  var all_opts = $(element + ' option');
  var all_opts_vals = {};
  all_opts.each(function(index, value) {
    json_store[jthis.attr('id') + '-' + index] = value.value;
  });

  jthis.removeClass('unset');
};


/**
 * Remove all elements starting with the prefix from an input's FormData
 * container.
 *
 * @param {Object} element an input element.
 * @param {string} prefix All data members with this prefix will be cleared.
 */
grr.forms.clearPrefix = function(element, prefix) {
  var form_data = $(element).closest('.FormData');

  if (form_data) {
    $.each(form_data.data(), function(k, v) {
      if (k == prefix || k.substring(0, prefix.length + 1) == prefix + '-') {
        form_data.removeData(k);
      }
    });
  }
};


grr.Renderer('EmbeddedProtoFormRenderer', {
  Layout: function(state) {
    $('#' + state.unique).click(function() {
      var jthis = $(this);

      if (jthis.hasClass('icon-plus')) {
        jthis.removeClass('icon-plus').addClass('icon-minus');

        var jcontent = $('#content_' + state.unique);

        // Load content from the server if needed.
        if (!jcontent.hasClass('Fetched')) {
          grr.update(state.renderer, 'content_' + state.unique, jthis.data());
        }

        jcontent.show();
      } else {
        // Flip the opener and remove the form.
        jthis.removeClass('icon-minus').addClass('icon-plus');
        $('#content_' + state.unique).hide();
      }
    });
  },

  RenderAjax: function(state) {
    // Mark the content as already fetched so we do not need to fetch again.
    $(state.id).addClass('Fetched');
  }
});


grr.Renderer('RepeatedFieldFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('button#add_' + unique).click(function(event) {
      var count = $(this).data('count');
      var new_id = 'content_' + unique + '_' + count;

      // Store the total count of members in the form.
      $(this).closest('.FormData').data()[state.prefix + '_count'] = count + 1;
      $(this).data('count', count + 1);

      $('#content_' + unique).append('<div id="' + new_id + '"/>');

      grr.update(state.renderer, new_id, {
        'index': count,
        'prefix': state.prefix,
        'owner': state.owner,
        'field': state.field});

      event.preventDefault();
    });
  },

  RenderAjax: function(state) {
    var unique = state.unique;

    $('button#remove_' + unique).click(function(event) {
      var form_id = '#' + unique;

      var data = $('#' + unique).data();
      grr.forms.clearPrefix(this, data.prefix + '-' + data.index);

      $(this).remove();
      $(form_id).remove();
    });
  }
});


grr.Renderer('StringTypeFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    if (value != null) {
      $('input#' + state.prefix).val(value).change();
    }
  }
});

grr.Renderer('EnumFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    if (value != null) {
      $('select#' + state.prefix).val(value).change();
    }
  }
});

grr.Renderer('ProtoBoolFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    if (value != null) {
      $('select#' + state.prefix).val(value).change();
    }
  }
});


grr.Renderer('OptionFormRenderer', {
  Layout: function(state) {
    $('#' + state.prefix + '-option').on('change', function() {
      grr.forms.inputOnChange(this);

      var data = $.extend({}, $(this).closest('.FormData').data());
      data['prefix'] = state.prefix;
      grr.update(state.renderer, state.unique + '-option-form', data);

      // First time the form appears, trigger the change event on the selector
      // to make the default choice appear.
    }).trigger('change');
  }
});


grr.Renderer('MultiFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var option = state.option || 'option';

    // This button is pressed when we want a new form.
    var addButton = $('#AddButton' + unique).click(function() {
      var data = $(this).closest('.FormData').data();
      var count = data[option + '_count'] || 1;
      var new_id = unique + '_' + count;

      data.item = count;
      data[option + '_count'] = count + 1;

      var new_div = $('<div class="alert fade in" id="' +
          new_id + '" data-item="' + count + '" >');

      new_div.on('close', function() {
        var item = $(this).data('item');
        grr.forms.clearPrefix(this, option + '_' + item);
      });

      new_div.insertBefore(this);

      grr.layout(state.renderer, new_id, data);
    });

    if (state.add_one_default) {
      // If "add_one_default" argument is true, first time we show the button
      // click it to make at least one option available.
      addButton.click();
    }
  }
});


grr.Renderer('SemanticProtoFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('#advanced_label_' + unique).click(function() {
      $('#advanced_controls_' + unique).toggle();

      var icon = $('#' + unique + ' .advanced-icon:last');
      if ($('#advanced_controls_' + unique).is(':visible')) {
        icon.removeClass('icon-chevron-right').addClass('icon-chevron-down');
      } else {
        icon.removeClass('icon-chevron-down').addClass('icon-chevron-right');
      }
    });

    $('#' + unique + ' i.advanced-icon').click(function() {
      $('#advanced_label_' + unique).trigger('click');
    });
  }
});


grr.Renderer('RDFDatetimeFormRenderer', {
  Layout: function(state) {
    $('#' + state.prefix + '_picker').datepicker({
      showAnim: '',
      changeMonth: true,
      changeYear: true,
      showOn: 'button',
      buttonImage: 'static/images/clock.png',
      buttonImageOnly: true,
      altField: '#' + state.prefix,
      onSelect: function(dateText, inst) {
        $('#' + state.prefix).trigger('change');
     }
    });
  }
});


grr.Renderer('MultiSelectListRenderer', {
  Layout: function(state) {
    var prefix = state.prefix;

    // Height hack as CSS isn't handled properly for multiselect.
    var multiselect_height = parseInt($('#' + prefix + ' option').length) * 15;
    $('#' + prefix).css('height', multiselect_height);
  }
});
