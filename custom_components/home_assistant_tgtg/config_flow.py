from homeassistant import config_entries
import voluptuous as vol

DOMAIN = "tgtg"

class ChineseAlmanacConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
    
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="中国老黄历", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("name", default="中国老黄历"): str,
            })
        )