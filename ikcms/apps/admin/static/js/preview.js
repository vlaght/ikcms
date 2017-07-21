function PreviewPanel(container){

    this.container = container;
    this.state = {
        opened: true,
    };
    this.pannel = null;

    this.setState = function(new_state){
        let state = {};
        $.extend(state, this.state, new_state);
        this.state = state;
        this.render();
    }

    this.close = function(){
        this.setState({opened: false})
    }

    this.open = function(){
        this.setState({opened: true})
    }

    this.render = function() {
        that = this;
        if(this.pannel){
            this.pannel.remove()
        }
        if(this.state.opened){
            var html =  
                '<div class="preview-panel">' +
					'<h2>Превью</h2>' +
					'<a class="close-button">-</a>' +
			    '</div>';
            this.pannel = $(html).appendTo(this.container);
            this.pannel.find('.close-button').click(function(e){
                e.stopPropagation();
                that.close();
            });
        }else{
            var html =  
                '<div class="preview-panel closed">' +
                    '<a class="close-button">+</a>' +
                '</div>';
            this.pannel = $(html).appendTo(this.container);
            this.pannel.find('.close-button').click(function(e){
                e.stopPropagation();
                that.open();
            });          
        }
    }
    this.render();
}


$(document).ready(function(e){
    $('[data-preview-edit]').each(function(index, block){
        block = $(block);
        var edit_url = block.data('preview-edit');
        var where = block.data('preview-where');
        var left = block.data('preview-left');
        var right = block.data('preview-right');
        var top = block.data('preview-top');
        var bottom = block.data('preview-bottom');
        var buttons = $(document.createElement('div'))
        buttons.addClass('preview-buttons');
        if(edit_url){
            var a = $(document.createElement('a'));
            a.attr('href', edit_url).html('Редактировать').appendTo(buttons)
        }
        if(where=='top'){
            buttons.prependTo(block);
        }else{
            buttons.appendTo(block);
        }
        if(left){
            buttons.css('left', left);
        }
        if(right){
            buttons.css('right', right); 
        }
        if(top){
            buttons.css('top', top); 
        }
        if(bottom){
            buttons.css('bottom', bottom); 
        }
    });
    let container = document.createElement('div');
    new PreviewPanel(container);
    document.body.appendChild(container);
});
