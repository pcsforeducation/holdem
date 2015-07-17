test:
	cd engine/ && java -cp bin com.theaigames.game.texasHoldem.TexasHoldem "python $(CURDIR)/bot/bot.py" "python $(CURDIR)/bot/template_bot.py" 2>../err.log 1>../out.log

zip:
	rm bot.zip && cd bot/ && zip -r ../bot.zip * -x *.pyc -x *~ -x template_bot.py -x static_hole/generate_data.py