var grr = window.grr || {};

grr.Renderer('UnauthorizedRenderer', {
  Layout: function(state) {
    var subject = state.subject;
    var message = state.message;

    grr.publish('unauthorized', subject, message);
    grr.publish('grr_messages', message);
  }
});

grr.Renderer('ACLDialog', {
  Layout: function(state) {
    $('#acl_dialog_submit').click(function(event) {
      $('#acl_form form').submit();
    });

    grr.subscribe('unauthorized', function(subject, message) {
      if (subject) {
        grr.layout('CheckAccess', 'acl_form', {subject: subject});
      }
    }, 'acl_dialog');
  }
});

grr.Renderer('GrantAccess', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;
    var acl = state.acl;
    var details_renderer = state.details_renderer;

    $('#' + unique + '_approve').click(function() {
      grr.update(renderer, unique + '_container', {
        acl: acl
      });
    });
    grr.layout(details_renderer,
               'details_' + unique,
               { acl: acl });
  },

  RefreshFromHash: function(state) {
    var renderer = state.renderer;
    var id = state.id;

    var hashState = grr.parseHashState();
    hashState.source = 'hash';
    grr.layout(renderer, id, hashState);
  }
});

grr.Renderer('CheckAccess', {
  Layout: function(state) {
    var unique = state.unique;
    var subject = state.subject;
    var refresh_after_form_submit = state.refresh_after_form_submit;
    var approval_renderer = state.approval_renderer;

    $('#acl_form_' + unique).submit(function(event) {
      if ($.trim($('#acl_reason').val()) == '') {
        $('#acl_reason_warning').show();
        event.preventDefault();
        return;
      }

      var state = {
        subject: subject,
        approver: $('#acl_approver').val(),
        reason: $('#acl_reason').val()
      };
      if ($('#acl_keepalive').is(':checked')) {
        state['keepalive'] = 'yesplease';
      }

      // When we complete the request refresh to the main screen.
      grr.layout(approval_renderer, 'acl_server_message', state,
                 function() {
                   if (refresh_after_form_submit) {
                     window.location = '/';
                   } else {
                     $('#acl_dialog').modal('hide');
                   }
                 });

      event.preventDefault();
    });

    if ($('#acl_dialog[aria-hidden=false]').size() == 0) {
      $('#acl_dialog').detach().appendTo('body');

      // TODO(user): cleanup a bit. We use update_on_show attribute in
      // NewHunt wizard to avoid reloading the modal when it's hidden and shown
      // again because ACL dialog interrupted the UI flow.
      var openedModal = $('.modal[aria-hidden=false]');
      openedModal.attr('update_on_show', 'false');
      openedModal.modal('hide');

      // Allow the user to request access through the dialog.
      $('#acl_dialog').modal('toggle');
    }

  },

  AccessOk: function(state) {
    var reason = state.reason;
    var silent = state.silent;

    grr.publish('hash_state', 'reason', reason);
    grr.state.reason = reason;
    if (!silent) {
      grr.publish('client_selection', grr.state.client_id);
    }
  }
});
