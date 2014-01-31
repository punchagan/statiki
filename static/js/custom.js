$('form#submit-repo').submit(
  function(evt){
    evt.preventDefault();

    var status = $('#status');
    var repo = $('label[for="repo_name"]').text() + $('input[name="repo_name"]').val();
    var text = 'Processing to create ' + repo + ' ...';
    $('#status').children().remove();
    $('input[name="repo_name"]').val('');
    var processing = $('<span id="processing">').text(text)
    status.append(processing);

    var xhr = $.post(
      '/manage',
      $(this).serialize(),
      function(data, status_code, jqxhr) {
        $('#status').children().remove()
        status.append($('<p>').text(data.message));
      }
    )
  }
);
