ep.ui.createTagsInput = function(source) {
    // partly from http://jqueryui.com/autocomplete/#multiple-remote
    function split(val) {
        return val.split(/,\s*/);
    }
    function extractLast(term) {
        return split(term).pop();
    }
    if ($.ui && $.ui.autocomplete) {
        $('input.tags-input').each(function() {
            var $that = $(this);
            $that.bind("keydown", function(event) {
                if (event.keyCode === $.ui.keyCode.TAB &&
                        $(this).data("ui-autocomplete").menu.active) {
                    event.preventDefault();
                }
            });
            $that.autocomplete({
                delay: 300,
                source: function(request, response) {
                    $.getJSON(source, {
                        term: extractLast(request.term)
                    }, response );
                },
                search: function() {
                    var term = extractLast(this.value);
                    if (term.length < 1) {
                      return false;
                    }
                },
                focus: function() {
                    return false;
                },
                select: function(event, ui) {
                    var terms = split(this.value);
                    terms.pop();
                    terms.push(ui.item.value);
                    terms.push("");
                    this.value = terms.join(", ");
                    return false;
                }
            });
        });
    }
};
