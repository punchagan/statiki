$('form#submit-repo').submit(
  function(evt){
    evt.preventDefault();

    var status = $('#status');
    var repo = $('label[for="repo_name"]').text() + $('input[name="repo_name"]').val();
    var text = 'Processing to create ' + repo + ' ...';
    status.children().remove();
    var processing = $('<span id="processing">').text(text)
    status.append(processing);

    var xhr = $.post('/create_repo', $(this).serialize());

    xhr.success(
      function(data, status_code, jqxhr) {
        continue_to_manage_step(data.created, data.exists, data.overwrite, data.full_name, data.message, data.contents);
        post_success(data, status_code, jqxhr);
      }
    ).fail(
      post_failure
    );

  }
);

var continue_to_manage_step = function(created, exists, overwrite, full_name, message, contents) {

  if (!created && !exists) {
    return;
  }

  if (created) {
    configure_travis(overwrite, full_name);
  } else {
    show_dialog(message, contents, overwrite, full_name);
  }

};

var configure_travis = function(overwrite, full_name){
    var xhr = $.post(
      '/manage', {'overwrite': overwrite, 'full_name': full_name}
    );

    xhr.success(post_success).fail(post_failure);

};

var post_failure = function(data, status_code, jqxhr) {
  var status = $('#status');
  status.children().remove();
  status.html(data.responseText);
  status.css('display', 'block');
  hide_form();

};

var post_success = function(data, status_code, jqxhr) {
  var status = $('#status');
  status.children().remove()
  status.append($('<p>').html(data.message));
  hide_form();

}

var hide_form = function(){
  var form = $('#repo-form');
  form.css('display', 'none');

  var status = $('#status');
  status.css('display', 'block');
}

var show_form = function(){
  var form = $('#repo-form');
  form.css('display', 'block');

  var status = $('#status');
  status.css('display', 'none');
}

var show_dialog = function(message, contents, overwrite, full_name) {
  var html='';
  contents.forEach(function(file) {
    html+= '<h2>' + file.name + '</h2>';
    html+= '<div class="box"><pre>' + file.content + '</pre></div>';
  });

  bootbox.dialog({
    message: html,
    title: '<p>' + message + '</p>',
    buttons: {
      success: {
        label: overwrite?'Overwrite':'Publish',
        className: "btn-success",
        callback: function(){
          configure_travis(overwrite, full_name);
          show_form();
        }
      },
      'Cancel': {
        callback: function(){
          post_failure({});
          show_form();
        }
      }
    }
  });
};
